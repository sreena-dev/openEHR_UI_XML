import requests, json
r = requests.get('http://localhost:8080/ehrbase/rest/ecis/v1/template/blood_pressure', auth=('admin', 'password'))
t = r.json()['webTemplate']['tree']
def p(n, d=0):
    print('  '*d + n.get('id', '??') + ' [' + n.get('rmType', '') + ']')
    for c in n.get('children', []):
        p(c, d+1)
p(t)
