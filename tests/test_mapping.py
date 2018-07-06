from smallprox import mapper


def test_mapping():
    map = eval("""
{'_local_ports': [], 
 '_local_address': '172.19.0.1', 
 'api-local.canopy.ninja': {
    'api': '172.19.0.20:9899', 
    'api/docs': '172.19.0.19:9191', 
    'api/letters': '172.19.0.17:9898', 
    'api/transcripts': '172.19.0.14:9892', 
    '': '172.19.0.13:8086'}, 
 'workflow-local.canopy.ninja': {
    'api': '172.19.0.20:9899', 
    'api/docs': '172.19.0.19:9191', 
    'api/letters': '172.19.0.17:9898', 
    'api/transcripts': '172.19.0.14:9892'}, 
 '*': {
   'api': '172.19.0.16:8888', 
   '': '172.19.0.10:8000', 
   'wg': '172.19.0.13:8086'}}""")

    assert ('172.19.0.10', '8000') == mapper.get_host_and_port(
        'app-local.canopy.ninja', '/', map)
    assert ('172.19.0.13', '8086') == mapper.get_host_and_port(
        'app-local.canopy.ninja', '/wg/users/0', map)
