# Manuscript (IEEE TEVC)

论文源码。目录名用 `manuscript/` 而不是 `paper/`，因为仓库根目录的 `.gitignore` 忽略了 `paper/`（放版权 PDF 用）。

## 结构

```
main.tex            主文件（IEEEtran journal 模板）
macros.tex          记号宏，所有符号在这里统一定义
refs.bib            参考文献（投稿前逐条对照原文核对）
sections/           每节一个文件，00_abstract … 11_conclusion
figures/            图（PDF 优先）
tables/             较大的表格可单独放这里再 \input
```

章节与证据的对应见项目文档《论文提纲_v1》；每个 section 文件开头的注释列出了该节的证据来源和"不能写"的说法。

## 编译

```bash
cd manuscript
latexmk -pdf main.tex
```

需要 IEEEtran（TeX Live 的 `texlive-publishers`；MiKTeX 会自动安装）。也可以把整个 `manuscript/` 打包上传到 Overleaf。

草稿期用 `\todo{}`（红）和 `\note{}`（蓝）做标记，投稿前全部清掉。
