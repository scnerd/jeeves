hypernames = dict(
)

class retagger(object):
    def __init__(self, base_dict):
        self.d = base_dict

    def __getitem__(self, item):
        return self.d[item] if item in self.d else "{" + item + "}"

    def __contains__(self, item):
        if type(item) == str:
            return True
        return False

    def __getattr__(self, item):
        return getattr(self.d, item)

hypernames = retagger(hypernames)

templates = {
    "main": """
{imports}

##############

{setup}

##############

{functions}

##############

{final}

##############

{launch}
""",
    "launch": """

""",
    "base_imports": ["json", "io", ("bz2", "zip"), "pickle"],
    "server_imports": ["flask", ('flask', ['Flask', 'request', 'send_file'])],
    "client_imports": ["requests", ('collections', ['OrderedDict'])],
    "server_setup": """
app = Flask(__name__)
""",
    "server_fetcher": {"json": "request.get_json()", "pickle": "request.files['JEEVES'].read()"},
    "client_fetcher": {"json": "content.decode('utf8')", "pickle": "content"},
    "client_packer_kwarg": {"json": "json=content",
                            "pickle": "files={'JEEVES': io.BytesIO(content)}"},
    "content_loaders": {"zip": "zip.decompress",
                        "nozip": ""},
    "content_savers":  {"zip": "zip.compress",
                        "nozip": ""},
    "packers": {"json": "json", "pickle": "pickle"},
    "unwrapper": """
def unwrap_{packer_type}_{saver_type}(content):
    content = {loader}(content)
    content = {packer}.loads(content)
    return content
""",
    "wrapper": """
def wrap_{packer_type}_{saver_type}(content):
    content = {packer}.dumps(content)
    content = {saver}(content)
    return content
""",
    "server_caller_func_regular": """
@app.route("{route}", methods=["GET", "POST"])
def jeeves_fetch_me_my_{name}():
    if not {noargs}:
        package = unwrap_{packer_type}_{saver_type}({server_fetcher})
        args = package['args']
        kwargs = package['kwargs']
    else:
        args = []
        kwargs = {{}}
    try:
        results = {func}(*args, **kwargs)
        success = True
    except Error as e:
        results = e
        success = False
    finally:
        if results is not None:
            return send_file(io.BytesIO(wrap_{packer_type}_{saver_type}((success, results))))
""",
    "server_caller_func_generator": """
@app.route("{route}", methods=["GET", "POST"])
def jeeves_fetch_me_some_{name}():
    raise NotImplementedError()
""",
    "server_caller_func_async": """
@app.route("{route}", methods=["GET", "POST"])
def jeeves_start_my_{name}():
    if not {noargs}:
        package = unwrap_{packer_type}_{saver_type}({server_fetcher})
        args = package['args']
        kwargs = package['kwargs']
    else:
        args = []
        kwargs = {{}}
    try:
        results = await {func}(*args, **kwargs)
        success = True
    except Error as e:
        print(e)
        results = e
        success = False
    finally:
        if results is not None:
            return send_file(io.BytesIO(wrap_{packer_type}_{saver_type}((success, results))))
""",
    "client_caller_func_regular": """
def {name}{signature}:
    args = list({make_args})
    kwargs = dict({make_kwargs})
    content = wrap_{packer_type}_{saver_type}({{'args': args, 'kwargs': kwargs}})
    result = requests.post("http://{hostname}:{port}{route}", {kwarg}).{client_fetcher}
    success, results = unwrap_{packer_type}_{saver_type}(result)
    if not success:
        raise results
    return results
""",
    "server_launcher": """
if __name__ == "__main__":
    app.run(host='{host_allow}', port={port})
"""
}


def create_import_line(imp):
    if type(imp) == str:
        return "import {}".format(imp)
    elif type(imp) == tuple:
        if len(imp) == 1:
            f = "import {}"
        elif len(imp) == 2:
            if type(imp[1]) == list:
                f = "from {} import {}"
                imp = [imp[0], ", ".join(imp[1])]
            else:
                f = "import {} as {}"
        elif len(imp) == 3:
            f = "from {} import {} as {}"
        else:
            raise RuntimeError("Unknown jeeves import argument: " + str(imp))
        return f.format(*imp)

def create_wrappers():
    return "\n".join(temp.format(packer_type=pt, saver_type=st, packer=templates['packers'][pt], saver=cont_temp[st], loader=cont_temp[st])
                       for temp, cont_temp in zip([templates['wrapper'], templates['unwrapper']],
                                                  [templates['content_savers'], templates['content_loaders']])
                       for pt in templates['packers']
                       for st in templates['content_loaders'])

