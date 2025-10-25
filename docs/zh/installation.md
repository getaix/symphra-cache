# 安装

要求：Python 3.9+

## 基本安装

```bash
pip install symphra-cache
```

## 可选组件

- 监控导出（Prometheus/StatsD）：
```bash
pip install "symphra-cache[monitoring]"
```
- 文档工具（MkDocs/mkdocstrings）：
```bash
pip install "symphra-cache[docs]"
```
- Redis 性能（hiredis）：
```bash
pip install "symphra-cache[hiredis]"
```

## 验证安装

```python
import symphra_cache
print(symphra_cache.__version__)
```
