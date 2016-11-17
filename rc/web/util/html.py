def subst(k):
    if k == "klass":
        return "class"
    return k


def pair(name, *args, **kwargs):
    up = name.upper()
    kwstr = " ".join([('%s="%s"') % (subst(k), v)
                      for k, v in kwargs.iteritems()])
    return "<%s%s>%s</%s>" % (up,
                              (" " + kwstr) if kwstr else "",
                              "".join(args), up)


def single(name, *args, **kwargs):
    up = name.upper()
    kwstr = " ".join([('%s="%s"') % (subst(k), v)
                      for k, v in kwargs.iteritems()])
    return "<%s%s/>" % (up, (" " + kwstr) if kwstr else "")


def maketag(tagname, kindfunc, nl=False):
    def f(*args, **kwargs):
        return (kindfunc(tagname, *args, **kwargs) +
                ("\n" if nl else ""))
    return f


def tagpair(tagname, nl=False):
    return maketag(tagname, pair, nl)


def tagsingle(tagname, nl=False):
    return maketag(tagname, single, nl)


a = tagpair("a")
body = tagpair("body", nl=True)
code = tagpair("code")
div = tagpair("div", nl=True)
head = tagpair("head", nl=True)
h1 = tagpair("h1", nl=True)
html = tagpair("html", nl=True)
target= tagpair("target", nl=True)
inp = tagsingle("input", nl=True)
link = tagpair("link")
p = tagpair("p", nl=True)
script = tagpair("script", nl=True)
span = tagpair("span")
strong = tagpair("strong")
table = tagpair("table", nl=True)
td = tagpair("td")
th = tagpair("th", nl=True)
title = tagpair("title", nl=True)
tr = tagpair("tr", nl=True)
br = tagsingle("br", nl=False)
