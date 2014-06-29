import logging
import os.path

logger = logging.getLogger('giza.content.includes')

from giza.files import expand_tree
from giza.serialization import ingest_yaml_doc
from giza.includes import generated_includes, included_recusively, include_files
from rstcloth.rstcloth import RstCloth

suppressed_page_prefixes = [
    '/includes/generated',
    '/includes/table',
    '/includes/steps',
    '/includes/install',
    '/includes/manpage',
    '/includes/toc',
    '/includes/ref-toc',
    '/includes/ref-spec',
    '/includes/metadata',
]

def write_include_index(conf):
    fd = include_file_data(conf)

    r = build_page(fd, conf)

    if r is not None:
        r.write(os.path.join(conf.paths.projectroot,
                             conf.paths.includes,
                             'generated',
                             'overview.rst'))

        logger.info('includes: generated /meta/includes source page.')


def include_file_data(conf):
    inc_path = os.path.join(conf.paths.includes)
    include_file_list = expand_tree(path=inc_path, input_extension=None)
    include_graph = include_files(conf=conf)

    recursive_use = included_recusively(include_graph)
    generated = generated_includes(conf)

    omni = {}
    for idx, fn in enumerate(include_file_list):
        incf = fn[len(conf.paths.source):]

        if fn.endswith('~'):
            continue

        for prefix in suppressed_page_prefixes:
            if incf.startswith(prefix):
                break
        else:
            omni[incf] = {
                'id': idx,
                'name': os.path.splitext(incf)[0],
                'path': incf,
            }

            if incf in generated:
                omni[incf]['generated'] = True
            else:
                omni[incf]['generated'] = False

            if incf in recursive_use:
                omni[incf]['recursive'] = True
            else:
                omni[incf]['recursive'] = False

            if incf in include_graph:
                omni[incf]['num_clients'] = len(include_graph[incf])

                omni[incf]['clients'] = []
                for cl in include_graph[incf]:
                    cl, ext = os.path.splitext(cl)

                    if ext == 'yaml':
                        continue
                    if (cl.startswith('/includes/generated/overview') or
                        cl.startswith('/includes/manpage-')):
                        continue

                    omni[incf]['clients'].append(cl)

                if len(omni[incf]['clients']) == 0:
                    omni[incf]['yaml_only'] = True
                else:
                    omni[incf]['yaml_only'] = False
            else:
                omni[incf]['clients'] = dict()
                omni[incf]['num_clients'] = 0

            with open(fn, 'r') as f:
                omni[incf]['content'] = [ ln.rstrip() for ln in f.readlines() ]

    return omni

def build_page(data, conf):
    fn = os.path.join(conf.paths.projectroot,
                      conf.paths.includes,
                      'metadata.yaml')

    if not os.path.exists(fn):
        return None
    else:
        iconf = ingest_yaml_doc(fn)

    r = RstCloth()

    r.title(iconf['title'])
    r.newline()
    r.directive('default-domain', iconf['domain'])
    r.newline()

    try:
        r.content(iconf['introduction'])
        r.newline()
    except KeyError:
        logger.debug('include meta file lacks an introduction.')

    r.directive(name='contents', arg='Included Files',
                fields=[ ('backlinks', 'none'),
                         ('class', 'long-toc'),
                         ('depth', 1),
                         ('local', ''),
                       ])
    r.newline()

    data = data.items()
    data.sort()
    for _, record in data:
        page_name = r.pre(record['name'])
        r.heading(text=page_name, char='-', indent=0)
        r.newline()

        r.heading('Meta', char='~', indent=0)
        r.newline()

        if record['num_clients'] == 0:
            r.content('{0} is not included in any files.'.format(page_name))

            r.newline()
            add_content(r, record)

        elif record['num_clients'] == 1:
            if record['yaml_only']:
                r.content('{0} is only included in yaml files.'.format(page_name))
                r.newline()
            else:
                link = r.role('doc', record['clients'][0])
                r.content('{0} is only included in {1}.'.format(page_name,  link))
                r.newline()

            add_meta(r, page_name, record)

            add_content(r, record)
        else:
            r.content('{0} is included in **{1}** files.'.format(page_name, record['num_clients']),
                      wrap=False)
            r.newline()

            add_meta(r, page_name, record)

            if record['yaml_only'] is False:
                clients = [ p for p in
                            record['clients']
                            if not p.startswith('/includes')
                            ]

                if len(clients) == 1:
                    client_link = r.role('doc', clients[0])

                    inc_str = '{0} is the only file that includes {1} that is not also an include.'
                    r.content(inc_str.format(client_link, page_name))

                    r.newline()
                else:
                    r.heading('Client Pages', char='~', indent=0)
                    r.newline()

                    for pg in clients:
                        client_link = r.role('doc', pg)

                        r.li(client_link, wrap=False)
                        r.newline()

            add_include_example(r, page_name, record['path'])
            add_content(r, record)

    return r

def add_include_example(r, name, path):
    r.heading('Example Use', char='~', indent=0)

    r.content('To include {0} in a document, use the following statement:'.format(name))
    r.newline()

    r.codeblock(content='.. include:: {0}'.format(path),
                language='rst')
    r.newline()

def add_content(r, record):
    r.heading('Content', char='~', indent=0)
    r.newline()
    r.codeblock(content=record['content'],
                language=os.path.splitext(record['path'])[1][1:],
                wrap=False)
    r.newline()

meta_strs = {
    'recursive': '{0} is included in another file used as an include.',
    'generated': '{0} is a generated file.'
}

def add_meta(r, page_name, record):
    for i in meta_strs.keys():
        if record[i] is True:
            r.content(meta_strs[i].format(page_name))
            r.newline()

def includes_tasks(conf, app):
    if (os.path.exists(os.path.join(conf.paths.projectroot, conf.paths.includes)) and
        os.path.exists(os.path.join(conf.paths.projectroot, conf.paths.source, 'meta'))):

        t = app.add('task')
        t.job = write_include_index
        t.args = [ conf ]
