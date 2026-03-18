# Arxiv Embodied AI Summarizer - 安装指南

## 作为Claude Code Skill安装

### 方法一：直接使用项目文件

1. **下载项目文件**
```bash
# 如果你有这个项目的压缩包
unzip arxiv_embodied_ai_summarizer.zip
cd arxiv_embodied_ai_summarizer

# 或者如果从git仓库克隆
git clone <repository_url>
cd arxiv_embodied_ai_summarizer
```

2. **安装Python依赖**
```bash
# 使用pip安装
pip install -r requirements.txt

# 或者使用uv（推荐）
uv pip install -r requirements.txt
```

3. **运行测试**
```bash
# 测试基本功能
python arxiv_summarizer.py --help

# 运行一个快速测试
python test_translation.py
```

### 方法二：作为Claude Code Skill包

1. **将项目打包为Skill**
```bash
# 确保所有必需文件存在
ls -la skill.yaml README_SKILL.md requirements.txt arxiv_summarizer.py

# 创建skill包目录结构
mkdir -p ~/.claude/skills/arxiv-embodied-ai-summarizer
cp -r * ~/.claude/skills/arxiv-embodied-ai-summarizer/
```

2. **在Claude Code中激活**
```bash
# 在Claude Code中
/skill install arxiv-embodied-ai-summarizer
```

## 系统要求

### 必需依赖
- **Python**: 3.8或更高版本
- **网络连接**: 用于下载论文和翻译服务
- **存储空间**: 至少1GB用于缓存论文和图像

### Python包依赖
```
requests>=2.28.0          # HTTP请求
beautifulsoup4>=4.11.0     # HTML解析
PyMuPDF>=1.21.0           # PDF处理
Pillow>=9.0.0             # 图像处理
deep-translator>=1.11.0    # 翻译服务
```

## 配置选项

### 基础配置
编辑 `config.py` 文件来自定义行为：

```python
# Arxiv搜索配置
ARXIV_CONFIG = {
    'search_query': 'cat:cs.RO OR cat:cs.AI OR cat:cs.LG',
    'max_results': 10,
    'days_back': 1
}

# 翻译配置
TRANSLATION_CONFIG = {
    'enabled': True,
    'target_language': 'zh',
    'fallback_services': ['google', 'bing', 'libre']
}

# 图像提取配置
IMAGE_CONFIG = {
    'enabled': True,
    'high_resolution': True,
    'architecture_focus': True
}
```

### 高级配置
```python
# 输出配置
OUTPUT_CONFIG = {
    'base_dir': './arxiv_papers',
    'include_images': True,
    'generate_summary': True,
    'markdown_format': True
}

# 性能配置
PERFORMANCE_CONFIG = {
    'parallel_downloads': True,
    'cache_enabled': True,
    'max_concurrent': 3,
    'timeout_seconds': 30
}
```

## 使用示例

### 基本使用
```bash
# 下载并总结今日论文
python arxiv_summarizer.py

# 只下载不总结
python arxiv_summarizer.py --download-only

# 处理指定PDF
python arxiv_summarizer.py --pdf path/to/paper.pdf
```

### 高级使用
```bash
# 自定义搜索参数
python arxiv_summarizer.py --max-results 20 --days-back 3

# 指定输出目录
python arxiv_summarizer.py --output-dir ./my_papers

# 禁用翻译
python arxiv_summarizer.py --no-translation

# 只提取图像
python arxiv_summarizer.py --images-only
```

## 测试功能

### 运行单元测试
```bash
# 测试翻译功能
python test_translation.py

# 测试PDF图像提取
python test_precise_screenshot.py

# 测试完整工作流
python test_full_workflow.py
```

### 验证安装
```bash
# 检查依赖
python -c "import requests, bs4, fitz, PIL; print('所有依赖已正确安装')"

# 检查网络连接
python -c "import requests; r=requests.get('http://arxiv.org'); print(f'Arxiv连接状态: {r.status_code}')"

# 检查翻译服务
python test_translation.py
```

## 故障排除

### 常见问题

1. **PyMuPDF安装失败**
```bash
# 在某些系统上需要额外依赖
sudo apt-get install libmupdf-dev  # Ubuntu/Debian
brew install mupdf-tools           # macOS
```

2. **翻译服务不可用**
```bash
# 检查网络连接
curl -I https://translate.google.com

# 测试替代翻译服务
python -c "from deep_translator import BingTranslator; print('Bing服务可用')"
```

3. **PDF下载失败**
```bash
# 检查Arxiv访问
curl -I http://arxiv.org/abs/2101.00001

# 检查用户代理设置
python -c "import requests; print(requests.get('http://arxiv.org').status_code)"
```

### 性能优化

1. **提高处理速度**
```python
# 在config.py中调整
PERFORMANCE_CONFIG['max_concurrent'] = 5  # 增加并发数
PERFORMANCE_CONFIG['cache_enabled'] = True  # 启用缓存
```

2. **减少内存使用**
```python
# 禁用高分辨率图像
IMAGE_CONFIG['high_resolution'] = False

# 限制处理的论文数量
ARXIV_CONFIG['max_results'] = 5
```

## 目录结构

安装后的典型目录结构：
```
arxiv_embodied_ai_summarizer/
├── skill.yaml              # Skill配置文件
├── README_SKILL.md         # Skill说明文档
├── INSTALL.md              # 安装指南（本文件）
├── requirements.txt        # Python依赖
├── arxiv_summarizer.py     # 主程序
├── config.py              # 配置文件
├── test_*.py              # 测试文件
└── output/                # 输出目录（运行后生成）
    ├── papers/
    ├── summaries/
    ├── images/
    └── translations/
```

## 支持和反馈

如果在安装或使用过程中遇到问题：

1. **检查系统要求**: 确保Python版本和依赖包版本符合要求
2. **查看日志**: 运行时添加 `--verbose` 参数查看详细日志
3. **测试网络**: 确保可以访问Arxiv和翻译服务
4. **重新安装**: 删除缓存后重新安装依赖包

这个skill设计为完全自包含，所有必需的功能都包含在项目文件中，无需外部服务依赖。