"""
CTM训练器
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, List
import json

from .ctm_layer import ContinuousThoughtModel
from ...utils import log


class StockTimeSeriesDataset(Dataset):
    """
    股票时序数据集

    每次返回一只股票的seq_len天历史数据作为样本
    """

    def __init__(self, price_data: pd.DataFrame,
                 seq_len: int = 120,
                 min_seq_len: int = 60,
                 feature_cols: List[str] = None):
        """
        Args:
            price_data: 行情数据，需包含 [code, date, open, high, low, close, volume, amount]
            seq_len: 序列长度 (交易日数)
            min_seq_len: 最小序列长度
            feature_cols: 特征列名列表
        """
        self.seq_len = seq_len
        self.min_seq_len = min_seq_len
        self.feature_cols = feature_cols or ['open', 'high', 'low', 'close', 'volume', 'amount']

        # 按日期排序
        self.price_data = price_data.sort_values(['code', 'date'])

        # 构建样本
        self.samples = self._build_samples()

        log.info(f"数据集构建完成: {len(self.samples)} 个样本, 特征维度: {len(self.feature_cols) + 2}")

    def _build_samples(self) -> List[dict]:
        """构建训练样本"""
        samples = []
        codes = self.price_data['code'].unique()

        # 特征列（含change_pct和turnover_rate）
        full_features = self.feature_cols.copy()
        if 'close' in full_features and 'volume' in full_features:
            full_features.extend(['change_pct', 'turnover_rate'])

        for code in codes:
            stock_data = self.price_data[self.price_data['code'] == code].copy()
            stock_data = stock_data.sort_values('date')

            # 确保有change_pct和turnover_rate
            if 'change_pct' not in stock_data.columns:
                stock_data['change_pct'] = stock_data['close'].pct_change() * 100
            if 'turnover_rate' not in stock_data.columns and 'volume' in stock_data.columns:
                stock_data['turnover_rate'] = stock_data['volume'] / stock_data['volume'].rolling(20).mean()

            all_features = full_features
            # 只保留存在的列
            all_features = [c for c in all_features if c in stock_data.columns]

            if len(all_features) < 4:
                continue

            for col in all_features:
                stock_data[col] = stock_data[col].fillna(method='ffill').fillna(0)

            feature_data = stock_data[all_features].values

            # 标准化
            mean = feature_data.mean(axis=0)
            std = feature_data.std(axis=0) + 1e-8
            feature_data = (feature_data - mean) / std

            # 构建序列样本
            n = len(feature_data)
            for i in range(self.min_seq_len, n):
                seq = feature_data[max(0, i - self.seq_len):i]
                if len(seq) < self.min_seq_len:
                    continue

                # 下期收益率作为标签
                future_return = stock_data['close'].iloc[min(i, n-1)] / stock_data['close'].iloc[max(0, i-1)] - 1

                samples.append({
                    'code': code,
                    'date': stock_data['date'].iloc[i-1],
                    'features': seq,
                    'label': future_return,
                    'norm_mean': mean,
                    'norm_std': std,
                })

        return samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        return {
            'features': torch.FloatTensor(sample['features']),
            'label': torch.FloatTensor([sample['label']]),
            'code': sample['code'],
            'date': sample['date'],
        }


class CTMTrainer:
    """
    CTM模型训练器
    """

    def __init__(self, model: ContinuousThoughtModel = None,
                 device: str = None,
                 model_dir: str = "models/ctm"):
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        if model is None:
            self.model = ContinuousThoughtModel(
                input_dim=8,
                d_model=64,
                n_layers=3,
                n_heads=4,
                n_scales=3,
                n_thought_steps=3,
            )
        else:
            self.model = model

        self.model = self.model.to(self.device)
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        log.info(f"CTM模型已初始化，设备: {self.device}")
        log.info(f"模型参数量: {sum(p.numel() for p in self.model.parameters()):,}")

    def train(self, train_data: StockTimeSeriesDataset,
              val_data: StockTimeSeriesDataset = None,
              epochs: int = 50,
              batch_size: int = 32,
              lr: float = 1e-3,
              weight_decay: float = 1e-4,
              warmup_epochs: int = 3,
              checkpoint_every: int = 5) -> dict:
        """
        训练CTM模型

        Args:
            train_data: 训练数据集
            val_data: 验证数据集
            epochs: 训练轮数
            batch_size: 批大小
            lr: 学习率
            weight_decay: 权重衰减
            warmup_epochs: 预热轮数
            checkpoint_every: 每N轮保存一次

        Returns:
            训练历史
        """
        train_loader = DataLoader(train_data, batch_size=batch_size,
                                  shuffle=True, num_workers=0,
                                  drop_last=True)

        val_loader = None
        if val_data:
            val_loader = DataLoader(val_data, batch_size=batch_size,
                                    shuffle=False, num_workers=0)

        optimizer = optim.AdamW(self.model.parameters(), lr=lr,
                               weight_decay=weight_decay)

        # 学习率调度
        def lr_lambda(epoch):
            if epoch < warmup_epochs:
                return epoch / warmup_epochs
            return max(0.1, 0.5 * (1 + np.cos(np.pi * (epoch - warmup_epochs) / (epochs - warmup_epochs))))

        scheduler = optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

        # 损失函数
        mse_loss = nn.MSELoss()
        ic_loss = IC_Loss()  # 自定义IC损失

        history = {'train_loss': [], 'val_loss': [], 'train_ic': [], 'val_ic': []}

        best_val_loss = float('inf')

        log.info(f"开始训练: {epochs} epochs, batch_size={batch_size}")

        for epoch in range(epochs):
            # 训练
            self.model.train()
            train_losses = []
            train_ics = []

            for batch in train_loader:
                features = batch['features'].to(self.device)  # [batch, seq, features]
                labels = batch['label'].squeeze(-1).to(self.device)  # [batch]

                optimizer.zero_grad()

                # 前向传播
                factors = self.model(features)  # Dict[str, [batch, 1]]

                # 组合因子预测
                pred = factors['ctm_momentum'].squeeze(-1)  # [batch]

                # 多任务损失: MSE + IC损失
                loss_mse = mse_loss(pred, labels)
                loss_ic = ic_loss(factors, labels)
                loss = loss_mse + 0.5 * loss_ic

                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()

                train_losses.append(loss.item())

                # 计算IC
                ic = self._compute_ic(pred.detach().cpu().numpy(),
                                      labels.detach().cpu().numpy())
                train_ics.append(ic)

            scheduler.step()

            # 验证
            val_loss = 0
            val_ic = 0
            if val_loader:
                self.model.eval()
                val_losses = []
                val_ics = []
                with torch.no_grad():
                    for batch in val_loader:
                        features = batch['features'].to(self.device)
                        labels = batch['label'].squeeze(-1).to(self.device)

                        factors = self.model(features)
                        pred = factors['ctm_momentum'].squeeze(-1)

                        loss = mse_loss(pred, labels) + 0.5 * ic_loss(factors, labels)
                        val_losses.append(loss.item())
                        val_ics.append(self._compute_ic(pred.cpu().numpy(),
                                                        labels.cpu().numpy()))

                val_loss = np.mean(val_losses)
                val_ic = np.mean(val_ics)

            train_loss = np.mean(train_losses)
            train_ic = np.mean(train_ics)

            history['train_loss'].append(train_loss)
            history['train_ic'].append(train_ic)
            if val_loader:
                history['val_loss'].append(val_loss)
                history['val_ic'].append(val_ic)

            lr_current = scheduler.get_last_lr()[0]
            if (epoch + 1) % 5 == 0 or epoch == 0:
                val_info = f", val_loss={val_loss:.6f}, val_ic={val_ic:.4f}" if val_loader else ""
                log.info(f"Epoch {epoch+1}/{epochs}: "
                        f"loss={train_loss:.6f}, ic={train_ic:.4f}"
                        f"{val_info}, lr={lr_current:.6f}")

            # 保存checkpoint
            if val_loader and val_loss < best_val_loss:
                best_val_loss = val_loss
                self.save_checkpoint('best.pt', epoch)
                log.info(f"保存最佳模型: val_loss={val_loss:.6f}")

            if (epoch + 1) % checkpoint_every == 0:
                self.save_checkpoint(f'checkpoint_{epoch+1}.pt', epoch)

        # 保存最终模型
        self.save_checkpoint('final.pt', epochs - 1)
        log.info("训练完成!")

        return history

    def _compute_ic(self, preds: np.ndarray, labels: np.ndarray) -> float:
        """计算IC (Information Coefficient)"""
        if len(preds) < 10:
            return 0
        return np.corrcoef(preds, labels)[0, 1]

    def save_checkpoint(self, filename: str, epoch: int):
        """保存模型检查点"""
        path = self.model_dir / filename
        torch.save({
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'model_config': {
                'input_dim': 8,
                'd_model': self.model.d_model,
                'n_layers': len(self.model.ctm_layers),
                'factor_names': self.model.factor_names,
            }
        }, path)
        log.debug(f"Checkpoint saved: {path}")

    def load_checkpoint(self, filename: str):
        """加载模型检查点"""
        path = self.model_dir / filename
        if not path.exists():
            log.warning(f"Checkpoint not found: {path}")
            return

        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        log.info(f"Model loaded: {path}")

    def predict_factors(self, price_data: pd.DataFrame,
                       codes: List[str] = None) -> pd.DataFrame:
        """
        批量预测因子

        Args:
            price_data: 行情数据
            codes: 股票代码列表，None则预测所有

        Returns:
            因子值DataFrame
        """
        if codes:
            data = price_data[price_data['code'].isin(codes)]
        else:
            data = price_data

        self.model.eval()
        results = []

        with torch.no_grad():
            for code in (codes or data['code'].unique()):
                stock_data = data[data['code'] == code].sort_values('date')
                if len(stock_data) < 60:
                    continue

                # 准备特征
                features = self._prepare_features(stock_data)
                features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)

                # 预测
                factors = self.model(features_tensor)

                # 最后一个时间步
                for name, values in factors.items():
                    stock_data = stock_data.copy()
                    stock_data[name] = values.squeeze(-1).item()

                stock_data = stock_data.dropna(subset=['ctm_momentum'])
                if 'ctm_momentum' in stock_data.columns:
                    results.append(stock_data[['code', 'date', 'ctm_momentum', 'ctm_reversal', 'ctm_volatility']])

        if not results:
            return pd.DataFrame()

        return pd.concat(results, ignore_index=True)

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


class IC_Loss(nn.Module):
    """自定义IC损失函数：最大化因子与下期收益的相关性"""

    def __init__(self):
        super().__init__()

    def forward(self, factors: dict, labels: torch.Tensor) -> torch.Tensor:
        """
        Args:
            factors: 因子字典
            labels: 下期收益率
        """
        loss = 0
        for name, values in factors.items():
            # 负的IC作为损失（最大化IC = 最小化负IC）
            pred = values.squeeze(-1)
            ic = self._pearson_correlation(pred, labels)
            loss -= ic  # 最大化相关性，所以减去

        return loss / len(factors)

    def _pearson_correlation(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """计算皮尔逊相关系数"""
        x_centered = x - x.mean()
        y_centered = y - y.mean()
        corr = (x_centered * y_centered).sum()
        corr /= (torch.sqrt((x_centered ** 2).sum()) * torch.sqrt((y_centered ** 2).sum()) + 1e-8)
        return corr
