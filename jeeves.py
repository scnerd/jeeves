import inspect
from collections import OrderedDict

try:
    from .templates import *
except SystemError:
    from templates import *

jeeves_defaults = dict(
    generator_batchsize="10",
    host_allow="127.0.0.1",
    hostname="localhost",
    port="5000",
    name="jeeves_mod",
    requires="",
    client_requires="",
    server_requires="",
)

defaults = dict(
    callable_prefix="",
    packer="pickle",
    content="zip",
    ignore="False",
    name="",
    route="",
    route_prefix="",
    requires="",
    client_requires="",
    server_requires="",
)


class Getter(object):
    def __init__(self, new, default=defaults):
        self.new = new
        self.default = default

    def __contains__(self, item):
        return item in self.new or item in self.default

    def __getitem__(self, item):
        return self.new[item] if item in self.new else self.default[item]

    def __call__(self, item):
        return self[item]


class JeevesFunction(object):
    def __init__(self, func, kwargs, cur_jeeves):
        self.process_signature(func)

        kwargs = Getter(kwargs, cur_jeeves.kwargs)
        packer_type = kwargs('packer')
        saver_type = kwargs('content')
        packer = templates['packers'][packer_type]
        loader = templates['content_loaders'][saver_type]
        saver = templates['content_savers'][saver_type]
        server_fetcher = templates['server_fetcher'][packer_type]
        client_fetcher = templates['client_fetcher'][packer_type]
        kwarg = templates['client_packer_kwarg'][packer_type]
        name = kwargs('name')
        route = kwargs('route_prefix').strip('/') + "/" + kwargs('route')
        if not route.startswith("/"):
            route = "/" + route
        func = kwargs('callable_prefix') + kwargs('name')
        hostname = kwargs('hostname')
        port = kwargs('port')
        fmt_kwargs = dict(packer=packer, loader=loader, saver=saver, packer_type=packer_type, saver_type=saver_type,
                          kwarg=kwarg, server_fetcher=server_fetcher, client_fetcher=client_fetcher, name=name,
                          route=route, func=func, hostname=hostname, port=port, noargs=self.noargs,
                          signature=self.signature, make_args=self.make_args, make_kwargs=self.make_kwargs)

        call_type = "generator" if inspect.isgeneratorfunction(func) \
            else "async" if inspect.iscoroutinefunction(func) \
            else "regular"

        self.server_code = (kwargs('server_requires') + "\n" + \
                           templates['server_caller_func_' + call_type].format(**fmt_kwargs)).strip()
        self.client_code = (kwargs('client_requires') + "\n" + \
                           templates['client_caller_func_' + call_type].format(**fmt_kwargs)).strip()
        self.requires = kwargs('requires')
        self.kwargs = kwargs

    def process_signature(self, func):
        signature = inspect.signature(func)
        self.signature = str(signature)
        make_args = []
        var_args = None
        make_kwargs = []
        var_kwargs = None
        self.noargs = len(signature.parameters) == 0
        for name, param in signature.parameters.items():
            if param.kind.name in ['POSITIONAL_ONLY', 'POSITIONAL_OR_KEYWORD']:
                make_args.append(name)
            elif param.kind.name in ['VAR_POSITIONAL']:
                var_args = name
            elif param.kind.name in ['KEYWORD_ONLY']:
                make_kwargs.append(name)
            elif param.kind.name in ['VAR_KEYWORD']:
                var_kwargs = name
        if var_args:
            self.make_args = "tuple([{}] + list({}))".format(", ".join(make_args), var_args)
        else:
            self.make_args = "({})".format("".join("{},".format(a) for a in make_args))
        if var_kwargs:
            self.make_kwargs = "OrderedDict([{}] + list({}.items()))".format(", ".join("('{0}', {0})".format(k) for k in make_kwargs), var_kwargs)
        else:
            self.make_kwargs = "OrderedDict([{}])".format(", ".join("('{0}', {0})".format(k) for k in make_kwargs))

    def to_server_code(self):
        return self.server_code

    def to_client_code(self):
        return self.client_code

    def to_requires(self):
        return self.requires


class Jeeves(object):
    def __init__(self, **kwargs):
        self.funcs = []
        self.kwargs = Getter(kwargs, jeeves_defaults)

    def to_server_code(self):
        imports = "\n".join(create_import_line(imp) for imp in templates['base_imports'] + templates['server_imports'])
        setup = [templates['server_setup']]
        setup += [self.kwargs('requires'), self.kwargs('server_requires')]
        setup += [f.to_requires() for f in self.funcs]
        setup += [create_wrappers()]
        setup = "\n\n".join(s.strip() for s in setup)
        body = "\n\n".join(f.to_server_code() for f in self.funcs)
        final = ""
        launch = templates['server_launcher'].format(port=self.kwargs('port'), host_allow=self.kwargs('host_allow'))
        return templates['main'].format(
            imports=imports.strip(),
            setup=setup.strip(),
            functions=body.strip(),
            final=final.strip(),
            launch=launch.strip()
        )

    def to_client_code(self):
        imports = "\n".join(create_import_line(imp) for imp in templates['base_imports'] + templates['client_imports'])
        setup = [self.kwargs('requires'), self.kwargs('client_requires')]
        setup += [f.to_requires() for f in self.funcs]
        setup += [create_wrappers()]
        setup = "\n\n".join(s.strip() for s in setup)
        body = "\n\n".join(f.to_client_code() for f in self.funcs)
        final = ""
        launch = ""
        return templates['main'].format(
            imports=imports.strip(),
            setup=setup.strip(),
            functions=body.strip(),
            final=final.strip(),
            launch=launch.strip()
        )

    def save_files(self, server_fname=None, client_fname=None):
        server_fname = server_fname if server_fname is not None else self.kwargs('name') + "_server.py"
        client_fname = client_fname if client_fname is not None else self.kwargs('name') + "_client.py"
        open(server_fname, 'w').write(self.to_server_code())
        open(client_fname, 'w').write(self.to_client_code())

    def spawn_server(self, port=None):
        pass

    def call(self, func, *args, **kwargs):
        pass


def get_jeeves_args(obj):
    config_line_prefix = "jeeves."

    doc = inspect.getdoc(obj)
    doc = "" if doc is None else doc
    doc_lines = [line.strip() for line in doc.split("\n")]

    comm = inspect.getcomments(obj)
    comm = "" if comm is None else comm
    comm_lines = [line.strip().lstrip("#").strip() for line in comm.split('\n')]

    lines = comm_lines + doc_lines
    lines = [line[len(config_line_prefix):] for line in lines if line.startswith(config_line_prefix)]
    lines = [line.partition("=") for line in lines]
    lines = [(arg.strip(), val.strip()) for arg, _, val in lines]
    return dict(lines)


def make_jeeves_from_module(module, **kwargs):
    insp_filter = inspect.isroutine
    kwargs.update(dict(callable_prefix=module.__name__ + "."))
    kwargs.update(get_jeeves_args(module))
    server_requires = "import {}\n".format(module.__name__)
    if 'requires' in kwargs:
        server_requires += kwargs['server_requires']
        del kwargs['server_requires']
    if 'name' in kwargs:
        name = kwargs['name']
        del kwargs['name']
    else:
        name = module.__name__.rpartition('.')[-1]
    jeeves = Jeeves(server_requires=server_requires, name=name, **kwargs)
    jeeves = make_jeeves_from_callables(jeeves, *inspect.getmembers(module, insp_filter), **kwargs)
    return jeeves


def make_jeeves_from_callables(jeeves: Jeeves = None, *callables, **kwargs):
    if jeeves is None:
        jeeves = Jeeves(**kwargs)
    config = Getter(kwargs)
    for func in callables:
        if type(func) == tuple:
            name, func = func
        else:
            name = func.__name__
        fargs = Getter({'name': name, 'route': name}, config)
        fargs = Getter(get_jeeves_args(func), fargs)
        if str(fargs('ignore')).lower() != "false":
            continue
        jeeves.funcs.append(JeevesFunction(func, fargs, jeeves))
    return jeeves


if __name__ == "__main__":
    import argparse, importlib

    parser = argparse.ArgumentParser()
    parser.add_argument("module")
    args = parser.parse_args()

    mod_to_jeeve = args.module
    mod_to_jeeve = importlib.import_module(mod_to_jeeve)
    j = make_jeeves_from_module(mod_to_jeeve)
    j.save_files()
