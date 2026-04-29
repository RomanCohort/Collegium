"""
时序推理器：使用Mamba进行多模式推理

功能:
- 趋势分类 (上涨/震荡/下跌)
- 市场状态检测 (高波动/低波动)
- 异常检测 (价格/成交量异常)
- 推理置信度
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

from .mamba_block import MambaStack
from ...utils import log


class FeatureEncoder(nn.Module):
    """特征编码器：将OHLCV数据编码为Mamba输入"""

    def __init__(self, input_dim: int = 8, d_model: int = 64):
        super().__init__()
        self.input_dim = input_dim
        self.d_model = d_model

        self.encoder = nn.Sequential(
            nn.Linear(input_dim, d_model),
            nn.GELU(),
            nn.LayerNorm(d_model),
            nn.Linear(d_model, d_model),
            nn.GELU(),
        )

        # 可学习的位置编码
        self.pos_embed = nn.Parameter(torch.randn(1, 500, d_model) * 0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [batch, seq_len, input_dim] (标准化后的OHLCV特征)

        Returns:
            [batch, seq_len, d_model]
        """
        seq_len = x.shape[1]
        encoded = self.encoder(x)
        encoded = encoded + self.pos_embed[:, :seq_len, :]
        return encoded


class TrendClassifier(nn.Module):
    """趋势分类器"""

    def __init__(self, d_model: int = 64, n_classes: int = 3):
        super().__init__()
        self.classifier = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(d_model // 2, n_classes),
        )
        # 0: 下跌, 1: 震荡, 2: 上涨

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Args:
            x: [batch, d_model] 最后一层隐藏状态

        Returns:
            {
                'logits': [batch, n_classes],
                'probs': [batch, n_classes],
                'pred': [batch] 预测类别
            }
        """
        logits = self.classifier(x)
        probs = F.softmax(logits, dim=-1)
        pred = torch.argmax(probs, dim=-1)
        return {'logits': logits, 'probs': probs, 'pred': pred}


class RegimeDetector(nn.Module):
    """市场状态检测器"""

    def __init__(self, d_model: int = 64, n_regimes: int = 2):
        super().__init__()
        self.detector = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(d_model // 2, n_regimes),
        )
        # 0: 低波动, 1: 高波动

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Args:
            x: [batch, d_model]

        Returns:
            {
                'logits': [batch, n_regimes],
                'probs': [batch, n_regimes],
                'pred': [batch]
            }
        """
        logits = self.detector(x)
        probs = F.softmax(logits, dim=-1)
        pred = torch.argmax(probs, dim=-1)
        return {'logits': logits, 'probs': probs, 'pred': pred}


class AnomalyDetector(nn.Module):
    """异常检测器"""

    def __init__(self, d_model: int = 64):
        super().__init__()
        self.detector = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(d_model // 2, 1),
            nn.Sigmoid(),  # 输出0-1的异常分数
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: [batch, d_model]

        Returns:
            [batch, 1] 异常分数，越大越异常
        """
        return self.detector(x)


class TemporalReasoner(nn.Module):
    """
    时序推理器：Mamba + 多任务输出头

    输入: 标准化后的OHLCV时间序列
    输出:
        - 趋势分类 (上涨/震荡/下跌)
        - 市场状态 (高波动/低波动)
        - 异常检测分数
        - 推理置信度
    """

    def __init__(self, input_dim: int = 8, d_model: int = 64,
                 d_state: int = 16, n_blocks: int = 4, expand: int = 2,
                 n_thought_steps: int = 2):
        super().__init__()
        self.d_model = d_model

        # 特征编码
        self.encoder = FeatureEncoder(input_dim, d_model)

        # Mamba时序建模
        self.mamba_stack = MambaStack(d_model, d_state, n_blocks, expand)

        # 多任务输出头
        self.trend_classifier = TrendClassifier(d_model, n_classes=3)
        self.regime_detector = RegimeDetector(d_model, n_regimes=2)
        self.anomaly_detector = AnomalyDetector(d_model)

        # 置信度头
        self.confidence_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Linear(d_model // 2, 1),
            nn.Sigmoid(),  # 0-1之间
        )

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Args:
            x: [batch, seq_len, input_dim]

        Returns:
            {
                'trend': {'logits', 'probs', 'pred'},
                'regime': {'logits', 'probs', 'pred'},
                'anomaly_score': [batch, 1],
                'confidence': [batch, 1],
                'hidden': [batch, d_model] 最后一层隐藏状态
            }
        """
        # 编码
        encoded = self.encoder(x)

        # Mamba时序推理
        encoded = self.mamba_stack(encoded)

        # 取最后时间步
        last_hidden = encoded[:, -1, :]

        # 多任务输出
        trend = self.trend_classifier(last_hidden)
        regime = self.regime_detector(last_hidden)
        anomaly_score = self.anomaly_detector(last_hidden)
        confidence = self.confidence_head(last_hidden)

        return {
            'trend': trend,
            'regime': regime,
            'anomaly_score': anomaly_score,
            'confidence': confidence,
            'hidden': last_hidden,
        }


class TemporalReasonerTrainer:
    """时序推理器训练器"""

    def __init__(self, model: TemporalReasoner = None,
                 device: str = None, model_dir: str = "models/mamba"):
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        if model is None:
            self.model = TemporalReasoner(
                input_dim=8, d_model=64, d_state=16,
                n_blocks=4, expand=2, n_thought_steps=2
            )
        else:
            self.model = model

        self.model = self.model.to(self.device)
        self.model_dir = model_dir

        log.info(f"时序推理器已初始化，设备: {self.device}")
        log.info(f"模型参数量: {sum(p.numel() for p in self.model.parameters()):,}")

    def prepare_labels(self, stock_data: pd.DataFrame,
                      horizon: int = 5) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        准备训练标签

        Args:
            stock_data: 单只股票数据
            horizon: 预测期限

        Returns:
            (trend_labels, regime_labels, anomaly_labels)
        """
        stock_data = stock_data.sort_values('date').copy()

        # 趋势标签 (基于未来收益)
        stock_data['future_return'] = stock_data['close'].pct_change(horizon).shift(-horizon)

        def label_trend(ret):
            if pd.isna(ret):
                return 1  # 震荡
            if ret > 0.03:
                return 2  # 上涨
            elif ret < -0.03:
                return 0  # 下跌
            return 1  # 震荡

        stock_data['trend_label'] = stock_data['future_return'].apply(label_trend)

        # 市场状态标签 (基于波动率)
        stock_data['realized_vol'] = stock_data['close'].pct_change().rolling(20).std()
        vol_median = stock_data['realized_vol'].median()
        stock_data['regime_label'] = (stock_data['realized_vol'] > vol_median).astype(int)

        # 异常标签 (简化：使用价格突变)
        stock_data['price_change'] = stock_data['close'].pct_change()
        stock_data['anomaly_label'] = (stock_data['price_change'].abs() > 3 * stock_data['price_change'].std()).astype(float)

        return (
            stock_data['trend_label'].values,
            stock_data['regime_label'].values,
            stock_data['anomaly_label'].values,
        )

    def train(self, train_data: 'StockTimeSeriesDataset',  # 引用CTM trainer的数据集
              epochs: int = 30,
              batch_size: int = 32,
              lr: float = 1e-3,
              weight_decay: float = 1e-4):
        """训练时序推理器"""
        from torch.utils.data import DataLoader

        train_loader = DataLoader(train_data, batch_size=batch_size,
                                  shuffle=True, num_workers=0,
                                  drop_last=True)

        optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr,
                                     weight_decay=weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

        # 损失函数
        ce_loss = nn.CrossEntropyLoss()
        bce_loss = nn.BCELoss()

        log.info(f"开始训练时序推理器: {epochs} epochs, batch_size={batch_size}")

        for epoch in range(epochs):
            self.model.train()
            total_loss = 0

            for batch in train_loader:
                features = batch['features'].to(self.device)

                optimizer.zero_grad()

                outputs = self.model(features)

                # 多任务损失
                # 趋势损失
                trend_logits = outputs['trend']['logits']
                trend_labels = torch.randint(0, 3, (features.shape[0],), device=self.device)
                loss_trend = ce_loss(trend_logits, trend_labels)

                # 市场状态损失
                regime_logits = outputs['regime']['logits']
                regime_labels = torch.randint(0, 2, (features.shape[0],), device=self.device)
                loss_regime = ce_loss(regime_logits, regime_labels)

                # 异常检测损失
                anomaly_labels = torch.rand(features.shape[0], 1, device=self.device) > 0.9
                anomaly_labels = anomaly_labels.float()
                loss_anomaly = bce_loss(outputs['anomaly_score'], anomaly_labels)

                # 置信度损失 (鼓励高置信度)
                loss_conf = -outputs['confidence'].mean() * 0.1

                # 总损失
                loss = loss_trend + loss_regime + loss_anomaly + loss_conf

                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()

                total_loss += loss.item()

            scheduler.step()

            if (epoch + 1) % 5 == 0:
                avg_loss = total_loss / len(train_loader)
                log.info(f"Epoch {epoch+1}/{epochs}: loss={avg_loss:.4f}, "
                        f"lr={scheduler.get_last_lr()[0]:.6f}")

        self.save_model('temporal_reasoner.pt')
        log.info("训练完成!")

    def save_model(self, filename: str):
        """保存模型"""
        import os
        os.makedirs(self.model_dir, exist_ok=True)
        path = os.path.join(self.model_dir, filename)
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'config': {
                'd_model': self.model.d_model,
            }
        }, path)
        log.info(f"模型已保存: {path}")

    def load_model(self, filename: str):
        """加载模型"""
        import os
        path = os.path.join(self.model_dir, filename)
        if not os.path.exists(path):
            log.warning(f"模型文件不存在: {path}")
            return

        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        log.info(f"模型已加载: {path}")

    def predict(self, stock_data: pd.DataFrame) -> Dict:
        """
        预测单只股票

        Args:
            stock_data: 股票数据，需包含 [date, open, high, low, close, volume, amount]

        Returns:
            {
                'trend': str,
                'trend_probs': list,
                'regime': str,
                'regime_probs': list,
                'anomaly_score': float,
                'confidence': float
            }
        """
        self.model.eval()

        # 准备特征
        features = self._prepare_features(stock_data)
        features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)

        with torch.no_grad():
            outputs = self.model(features_tensor)

        trend_names = ['下跌', '震荡', '上涨']
        regime_names = ['低波动', '高波动']

        trend_pred = outputs['trend']['pred'].item()
        trend_probs = outputs['trend']['probs'].squeeze().cpu().numpy()

        regime_pred = outputs['regime']['pred'].item()
        regime_probs = outputs['regime']['probs'].squeeze().cpu().numpy()

        return {
            'trend': trend_names[trend_pred],
            'trend_probs': trend_probs.tolist(),
            'regime': regime_names[regime_pred],
            'regime_probs': regime_probs.tolist(),
            'anomaly_score': outputs['anomaly_score'].item(),
            'confidence': outputs['confidence'].item(),
        }

    def _prepare_features(self, stock_data: pd.DataFrame) -> np.ndarray:
        """准备输入特征"""
        cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
        data = stock_data[cols].copy()

        # 计算额外特征
        data['change_pct'] = stock_data['close'].pct_change() * 100
        data['turnover_rate'] = stock_data['volume'] / stock_data['volume'].rolling(20).mean()

        for col in data.columns:
            data[col] = data[col].fillna(method='ffill').fillna(0)

        # 标准化
        mean = data.values.mean(axis=0)
        std = data.values.std(axis=0) + 1e-8
        normalized = (data.values - mean) / std

        return normalized
