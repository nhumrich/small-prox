from smallprox import mapper


def test_mapping_only_labels():
    map_ = {'_local_ports': [],
           '_local_address': '172.19.0.1',
           'api-local.example.com': {
               'api': '172.19.0.20:9899',
               'api/foo': '172.19.0.19:9191',
               'api/bar': '172.19.0.17:9898',
               'api/baz': '172.19.0.14:9892',
               '': '172.19.0.13:8086'},
           'auth-local.example.com': {
               'api': '172.19.0.20:9899',
               'api/foo': '172.19.0.19:9191',
               'api/bar': '172.19.0.17:9898',
               'api/baz': '172.19.0.14:9892'},
           '*': {
               'api': '172.19.0.16:8888',
               '': '172.19.0.10:8000',
               'wg': '172.19.0.13:8086'}}

    assert ('172.19.0.10', '8000') == mapper.get_host_and_port(
        'app-local.example.com', '/', map_)
    assert ('172.19.0.13', '8086') == mapper.get_host_and_port(
        'app-local.example.com', '/wg/users/0', map_)


def test_mapping_local():
    map_ = {'_local_ports': ['/api=8080', 'api-local.example.com=8181'],
           '_local_address': '172.19.0.1',
           '*': {}}

    mapper.update_local_overrides(map_)

    assert ('172.19.0.1', '8080') == mapper.get_host_and_port(
        'app-local.example.com', '/api', map_)
    assert ('172.19.0.1', '8181') == mapper.get_host_and_port(
        'api-local.example.com', '/app', map_)

