# -*- coding: utf-8 -*-
"""HTML 转 PDF 独立小工具(Windows)
原理: 调用系统自带 Edge(headless Chromium) 打印, 零依赖、保真(CSS/图片原样)

用法:
    python html2pdf.py "C:\\path\\文章.html"                # 输出到 HTML 同目录同名 .pdf
    python html2pdf.py "in.html" "D:\\out\\自定义.pdf"       # 指定输出路径
    python html2pdf.py folder_or_html ...                   # 支持批量(目录=该目录全部 html)
"""
import os
import subprocess
import sys
import glob

_EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\ProgramData\Microsoft\Windows\AppRepository\Packages\Microsoft.MicrosoftEdge_8wekyb3d8bbwe\MicrosoftEdge.exe",
]


def find_edge() -> str:
    for c in _EDGE_CANDIDATES:
        if os.path.exists(c):
            return c
    # 注册表/where 兜底
    try:
        out = subprocess.run(["where", "msedge"], capture_output=True, text=True).stdout.strip()
        if out:
            return out.splitlines()[0]
    except Exception:
        pass
    raise FileNotFoundError("未找到 Edge 浏览器(系统需 Win10/11 自带)")


def convert(html_path: str, pdf_path: str | None = None) -> str:
    """单个 HTML -> PDF; 返回输出 PDF 路径"""
    html_path = os.path.abspath(html_path)
    if not os.path.exists(html_path):
        raise FileNotFoundError(html_path)
    if not pdf_path:
        pdf_path = os.path.splitext(html_path)[0] + ".pdf"
    pdf_path = os.path.abspath(pdf_path)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    edge = find_edge()
    url = "file:///" + html_path.replace("\\", "/")
    # headless 打印(新老参数兼容: 新版 --headless=new 同样支持 --print-to-pdf)
    cmd = [
        edge, "--headless", "--disable-gpu", "--no-first-run",
        "--disable-extensions",
        f"--print-to-pdf={pdf_path}",
        url,
    ]
    # 新版 Edge headless 有时需要 --disable-dev-shm-usage(低内存机)
    print(">>> " + " ".join(cmd[:3]) + ' ...')
    subprocess.run(cmd, check=True, timeout=90,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(pdf_path):
        raise RuntimeError("转换失败: 未生成 PDF 文件")
    size = os.path.getsize(pdf_path) / 1024
    print(f"✅ 已转换: {pdf_path} ({size:.0f} KB)")
    return pdf_path


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    arg = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    if os.path.isdir(arg):
        htmls = sorted(glob.glob(os.path.join(arg, "*.html")))
        if not htmls:
            print(f"目录内无 html: {arg}")
            sys.exit(1)
        print(f"批量转换 {len(htmls)} 个 HTML...")
        for h in htmls:
            try:
                convert(h)
            except Exception as e:
                print(f"  ⚠ {os.path.basename(h)}: {e}")
    else:
        convert(arg, out)


if __name__ == "__main__":
    main()