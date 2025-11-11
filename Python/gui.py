from tkinter import Tk
from tkinter.ttk import Style, Notebook
from forms import PipelineBuilderUI_PW9, Dream3dMicrotextureAnalysis, UserGuide
from __init__ import __version__


def main():
    root = Tk()
    w, h = 700, 610
    tabControl = Notebook(root)
    root.geometry("%sx%s+300+300" % (w, h))
    root.title(f"Microtexture Analysis Workflow v{__version__}")

    s = Style()
    s.configure("TFrame", background="white")
    s.configure("TLabel", background="white")
    s.configure("TButton", background="black", foreground="black")

    tab1 = PipelineBuilderUI_PW9()
    tab2 = Dream3dMicrotextureAnalysis()
    tab3 = UserGuide()

    tabControl.add(tab1, text="1)  Pipeline Builder")
    tabControl.add(tab2, text="2)  Microtexture Analysis")
    tabControl.add(tab3, text="User Guide")
    tabControl.pack(expand=1, fill="both")

    root.mainloop()

    # Get rid of the error message if the user clicks the close icon instead of the submit button
    try:
        root.destroy()
    except:
        pass

    return


if __name__ == "__main__":
    main()
