"""
DeepSeek API 客户端

兼容OpenAI接口格式，支持DeepSeek API调用
"""

import os
import time
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import requests

from ...utils import log


class DeepSeekClient:
    """
    DeepSeek API 客户端

    支持:
    - Chat API (对话)
    - 反思提示生成
    - 响应缓存
    - 速率限制
    """

    def __init__(self, api_key: str = None,
                 base_url: str = "https://api.deepseek.com/v1",
                 model: str = "deepseek-chat",
                 timeout: int = 60,
                 max_retries: int = 3):
        """
        Args:
            api_key: DeepSeek API密钥
            base_url: API基础URL
            model: 模型名称
            timeout: 请求超时(秒)
            max_retries: 最大重试次数
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            log.warning("未设置DeepSeek API密钥，请设置环境变量 DEEPSEEK_API_KEY")

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

        # 缓存
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = timedelta(hours=6)

        # 速率限制
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 秒

        log.info(f"DeepSeek客户端初始化完成，模型: {self.model}")

    def chat(self, messages: List[Dict[str, str]],
             temperature: float = 0.7,
             max_tokens: int = 2048,
             stop: List[str] = None) -> str:
        """
        调用Chat API

        Args:
            messages: 消息列表 [{"role": "user/assistant/system", "content": "..."}]
            temperature: 温度参数 (0-1)
            max_tokens: 最大token数
            stop: 停止词列表

        Returns:
            助手回复内容
        """
        # 检查缓存
        cache_key = self._make_cache_key(messages, temperature)
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.now() - cached['timestamp'] < self.cache_ttl:
                log.debug("使用缓存的API响应")
                return cached['content']

        # 速率限制
        self._rate_limit()

        # 发送请求
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if stop:
            payload["stop"] = stop

        url = f"{self.base_url}/chat/completions"

        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    url,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()

                content = result['choices'][0]['message']['content']

                # 缓存
                self.cache[cache_key] = {
                    'content': content,
                    'timestamp': datetime.now(),
                }

                return content

            except requests.exceptions.Timeout:
                log.warning(f"请求超时 (尝试 {attempt+1}/{self.max_retries})")
            except requests.exceptions.RequestException as e:
                log.warning(f"请求失败 (尝试 {attempt+1}/{self.max_retries}): {e}")

            if attempt < self.max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避

        return "API调用失败，请稍后重试"

    def _rate_limit(self):
        """速率限制"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _make_cache_key(self, messages: List[Dict], temperature: float) -> str:
        """生成缓存键"""
        content = json.dumps(messages, ensure_ascii=True)
        return f"{content[:200]}_{temperature}"

    def reflection_prompt(self, context: Dict) -> str:
        """
        生成反思提示

        Args:
            context: 市场上下文
                - date: 当前日期
                - codes: 持仓股票列表
                - scores: 综合得分
                - trend: 趋势判断
                - volatility: 波动率
                - anomaly_score: 异常检测分数
                - recent_returns: 最近收益
                - market_sentiment: 市场情绪

        Returns:
            格式化后的提示词
        """
        return f"""你是一位经验丰富的量化交易策略分析师。你的任务是进行**反思性审查**，评估当前交易信号的质量和风险。

## 当前市场上下文

**日期**: {context.get('date', 'N/A')}
**持仓标的**: {', '.join(context.get('codes', ['N/A'])[:10])}
**综合得分**: {context.get('scores', 'N/A')}
**趋势判断**: {context.get('trend', 'N/A')}
**市场波动率**: {context.get('volatility', 'N/A')}
**异常检测**: {context.get('anomaly_score', 'N/A')}
**近期收益**: {context.get('recent_returns', 'N/A')}
**市场情绪**: {context.get('market_sentiment', 'N/A')}

## 反思任务

请从以下三个维度进行反思性审查：

### 1. 验证性反思 (Verification)
- 当前信号是否与市场状态匹配？
- 趋势判断是否与实际走势一致？
- 综合得分是否合理？

### 2. 风险性反思 (Risk Assessment)
- 是否有潜在风险被忽视？
- 异常检测是否暗示异常市场行为？
- 市场情绪是否过度乐观/悲观？

### 3. 生成性反思 (Generation)
- 如何调整权重以更好地适应市场？
- 是否需要调整持仓规模？
- 是否有新的风险敞口需要关注？

## 输出格式

请严格按以下JSON格式输出，不要包含其他内容：

```json
{{
    "confidence": 0.85,
    "weight_adjustment": 1.1,
    "risk_flags": ["高波动", "异常成交量"],
    "reasoning_chain": [
        "观察到近期波动率上升3倍",
        "建议降低整体仓位20%",
        "增加防御性配置"
    ],
    "signal_quality": "良好",
    "recommendations": [
        "降低科技股仓位",
        "增加现金持仓",
        "关注期权对冲机会"
    ]
}}
```

**confidence**: 置信度 (0-1)，表示信号可靠程度
**weight_adjustment**: 权重调整因子 (>1表示放大, <1表示缩小)
**risk_flags**: 风险标记列表
**reasoning_chain**: 推理链（你的思考过程）
**signal_quality**: 信号质量评级 ("优秀"/"良好"/"一般"/"较差")
**recommendations**: 调整建议列表

请现在开始反思性审查："""

    def batch_reflection(self, contexts: List[Dict]) -> List[Dict]:
        """
        批量反思（每月/每周调用一次）

        Args:
            contexts: 上下文列表

        Returns:
            反思结果列表
        """
        results = []
        for i, ctx in enumerate(contexts):
            log.info(f"反思进度: {i+1}/{len(contexts)}")
            result = self._single_reflection(ctx)
            results.append(result)
            time.sleep(1)  # 避免API限流

        return results

    def _single_reflection(self, context: Dict) -> Dict:
        """执行单次反思"""
        prompt = self.reflection_prompt(context)
        messages = [
            {"role": "system", "content": "你是一位专业的量化交易策略分析师。"},
            {"role": "user", "content": prompt}
        ]

        response = self.chat(messages, temperature=0.3)
        return self._parse_reflection_response(response)

    def _parse_reflection_response(self, response: str) -> Dict:
        """解析反思响应"""
        # 尝试提取JSON
        try:
            # 尝试直接解析
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            pass

        try:
            # 尝试从markdown代码块中提取
            import re
            match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if match:
                result = json.loads(match.group(1))
                return result
        except Exception as e:
            log.warning(f"解析反思响应失败: {e}")

        # 解析失败时返回默认值
        return {
            "confidence": 0.5,
            "weight_adjustment": 1.0,
            "risk_flags": [],
            "reasoning_chain": ["解析失败，使用默认值"],
            "signal_quality": "一般",
            "recommendations": [],
        }

    def save_api_config(self, config_path: str):
        """保存API配置"""
        config = {
            "base_url": self.base_url,
            "model": self.model,
        }
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

    def load_api_config(self, config_path: str):
        """加载API配置"""
        if not Path(config_path).exists():
            return

        with open(config_path, 'r') as f:
            config = json.load(f)
            self.base_url = config.get("base_url", self.base_url)
            self.model = config.get("model", self.model)
