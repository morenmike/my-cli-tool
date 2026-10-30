# my-cli-tool

一个**零第三方依赖**的 Python 命令行小工具：扫描指定目录，按文件扩展名分组统计数量与总大小，并列出体积最大的文件。跨 Windows / macOS / Linux，纯标准库实现。

## 功能

- 按扩展名汇总：文件数量、总大小（自动换算成 B / KB / MB / GB）
- 递归遍历子目录，可限制最大深度，也可只看当前目录
- 跳过以 `.` 开头的隐藏文件与目录
- 按总大小或文件数量排序，可只看前 N 类
- 支持 `--json` 输出，方便脚本二次处理
- 不跟随符号链接，避免目录环导致死循环

## 安装

需要 Python 3.8+。在仓库根目录执行：

```bash
pip install .
```

安装后即可使用 `filestats` 命令；不想安装也可以直接以模块方式运行：

```bash
python -m my_cli_tool <目录>
```

## 用法

```bash
filestats [目录] [选项]
```

| 选项 | 说明 | 默认 |
| --- | --- | --- |
| `directory` | 要扫描的目录 | 当前目录 `.` |
| `--no-recursive` | 不进入子目录 | 递归 |
| `--max-depth N` | 最大递归深度（0 表示仅根目录） | 不限制 |
| `--skip-hidden` | 跳过名称以 `.` 开头的文件/目录 | 关闭 |
| `--sort size\|count` | 按总大小或数量排序 | `size` |
| `--top N` | 只显示前 N 类扩展名与最大文件 | `10` |
| `--json` | 输出机器可读 JSON | 关闭 |

## 示例

统计当前目录（递归），按大小排序，显示前 10 类：

```bash
filestats
```

只看 `~/Downloads` 第一层，跳过隐藏文件，按数量排序：

```bash
filestats ~/Downloads --no-recursive --skip-hidden --sort count
```

输出 JSON 供其他脚本使用：

```bash
filestats ./project --json > stats.json
```

文本输出示例：

```text
Directory: /home/user/Downloads
Total files: 128  |  Total size: 1.4 GB

Extension             Count          Size
----------------------------------------
zip                       12        812.3 MB
pdf                       45        310.7 MB
jpg                       61        289.5 MB
py                        10         12.1 MB

Largest files (top 10):
       186.2 MB  /home/user/Downloads/dataset.zip
        92.4 MB  /home/user/Downloads/backup.tar.gz
```

## 运行测试

```bash
python -m unittest discover -s tests -v
```

## 目录结构

```
my-cli-tool/
├── my_cli_tool/
│   ├── __init__.py
│   ├── __main__.py      # 支持 python -m my_cli_tool
│   └── cli.py           # 核心扫描逻辑与命令行入口
├── tests/
│   └── test_cli.py
├── pyproject.toml
├── README.md
└── LICENSE
```

## License

MIT，详见 [LICENSE](LICENSE)。
