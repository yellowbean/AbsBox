import pathlib,os,sys
try:
    # Python <= 3.8
    from importlib_resources import files
except ImportError:
    from importlib.resources import files
# from pytest_notebook import example_nbs
from pytest_notebook.nb_regression import NBRegressionFixture

#sys.path.prepend(os.path.abspath("absbox"))
#sys.path = ['../../'] + sys.path

thisFile = os.path.abspath(__file__)
p = pathlib.Path(thisFile).parent.parent.parent

sys.path.insert(0,str(p))

print(sys.path)


NbFolder = os.path.join("docs","source","nbsample")

fixture = NBRegressionFixture(exec_timeout=50)
fixture.diff_color_words = False

#sys.path.insert(0,"../../../")

# def test_run():
#     NbList = [str(x) for x in pathlib.Path(NbFolder).rglob("*.ipynb")]
#     for nb in NbList:
#         print(f"running nb {nb}")
#         fixture.check(nb)


if __name__ == "__main__":
    #test_run()
    pass
