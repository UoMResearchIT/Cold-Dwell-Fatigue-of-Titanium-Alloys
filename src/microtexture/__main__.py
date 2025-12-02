"""Allow running the package as: python -m microtexture [gui]"""
import sys

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[-1].endswith("gui"):
        from microtexture.gui import main as gui_main
        gui_main()
    else:
        from microtexture.cli import main as cli_main
        cli_main()
