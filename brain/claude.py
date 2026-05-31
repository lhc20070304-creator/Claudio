"""CLAUDE.PY · 大脑适配器 — 多模型支持 + 多轮对话"""
import json
import re
import os
import requests

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")


def _load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class BrainAdapter:
    def __init__(self):
        cfg = _load_config()
        # 支持 deepseek / claude / openai 三种后端
        backend = cfg.get("backend", "deepseek")
        if backend == "claude":
            provider = cfg["claude"]
            self.api_key = provider["api_key"]
            self.base_url = provider.get("base_url", "https://api.anthropic.com").rstrip("/")
            self.model = provider.get("model", "claude-sonnet-4-6")
            self.url = f"{self.base_url}/v1/messages"
            self.provider = "claude"
        elif backend == "openai":
            provider = cfg["openai"]
            self.api_key = provider["api_key"]
            self.base_url = provider.get("base_url", "https://api.openai.com").rstrip("/")
            self.model = provider.get("model", "gpt-4o")
            self.url = f"{self.base_url}/v1/chat/completions"
            self.provider = "openai"
        else:
            provider = cfg["deepseek"]
            self.api_key = provider["api_key"]
            self.base_url = provider.get("base_url", "https://api.deepseek.com").rstrip("/")
            self.model = provider.get("model", "deepseek-chat")
            self.url = f"{self.base_url}/chat/completions"
            self.provider = "deepseek"

    def ask(self, system_prompt, user_message, history=None, raw=False):
        """发送请求，支持多轮对话

        history: [(role, content), ...] 之前的对话轮次（user/assistant 交替）
        raw=True: 返回纯文本（用于品味分析等场景）
        """
        is_claude = self.provider == "claude"

        if is_claude:
            return self._ask_claude(system_prompt, user_message, history, raw)
        else:
            return self._ask_openai_compat(system_prompt, user_message, history, raw)

    def _ask_openai_compat(self, system_prompt, user_message, history, raw):
        """DeepSeek / OpenAI 兼容调用"""
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for role, content in history:
                if content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.85,
            "max_tokens": 2000 if raw else 1500,
        }
        if not raw:
            payload["response_format"] = {"type": "json_object"}

        content = ""
        try:
            resp = requests.post(self.url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            if raw:
                return {"say": content}
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', content) if content else None
            if match:
                return json.loads(match.group())
            return {"say": content or "", "play": [], "reason": "parse error", "segue": ""}
        except Exception as e:
            return {"say": f"抱歉，信号不太好… {str(e)[:50]}", "play": [], "reason": str(e), "segue": ""}

    def _ask_claude(self, system_prompt, user_message, history, raw):
        """Anthropic Claude API 调用"""
        messages = []
        if history:
            for role, content in history:
                if content:
                    # Claude uses 'user'/'assistant' roles
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": self.model,
            "system": system_prompt,
            "messages": messages,
            "max_tokens": 2000 if raw else 1500,
            "temperature": 0.85,
        }

        content = ""
        try:
            resp = requests.post(self.url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            content = data["content"][0]["text"]
            if raw:
                return {"say": content}
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
            return {"say": content, "play": [], "reason": "", "segue": ""}
        except json.JSONDecodeError:
            return {"say": content or "", "play": [], "reason": "parse error", "segue": ""}
        except Exception as e:
            return {"say": f"抱歉，信号不太好… {str(e)[:50]}", "play": [], "reason": str(e), "segue": ""}


brain = BrainAdapter()
