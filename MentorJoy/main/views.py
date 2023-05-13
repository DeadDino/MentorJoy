from django.shortcuts import render, redirect, HttpResponseRedirect
from django.http import HttpResponse
from django.urls import reverse
from django.http import FileResponse
import json
import requests
import copy

def index(request):
    if is_valid(request.COOKIES.get('token')): return redirect('/templates')
    return redirect('/login')

def login(request):
    response = HttpResponse(render(request, "index.html"))
    if request.method == 'POST':
        data = request_login(request.POST['name'], request.POST['password'])
        if data.status_code == 401: return render(request, 'index.html', {'error': True})
        response = HttpResponseRedirect('templates')
        response.set_cookie('token', data.json()['accessToken'])
    return response

def new_project(request):
    token = request.COOKIES.get('token')
    if not is_valid(token): return redirect('login')
    if request.method == 'POST':
        result = request_api('POST', 'app/sample/create', None, token).json() if not request.POST.get('id') else get_template(int(request.POST.get('id')), token)

        #Get teacher ФИО
        teacher = request.POST['q1'].split() or ['', '', '']

        result['teacher']['firstname'] = teacher[1]
        result['teacher']['surname'] = teacher[0]
        result['teacher']['lastname'] = teacher[2]
        result['teacher']['status'] = request.POST['q2']

        # Get teacher ФИО
        head = request.POST['q3'].split() or ['', '', '']

        result['headTeacher']['firstname'] = head[1]
        result['headTeacher']['surname'] = head[0]
        result['headTeacher']['lastname'] = head[2]
        result['headTeacher']['status'] = request.POST['q4']

        result['year'] = int(request.POST['q5'])

        result['programName'] = request.POST['q6']
        result['programShortName'] = request.POST['q7']
        result['programNameEnglish'] = request.POST['q10']

        result['description'] = request.POST['q9']
        result['byDocument'] = request.POST['q8']

        result['department'] = get_department(request.POST['q12'], token)
        result['clazz'] = get_clazz(request.POST['q13'], token)

        print(result)
        print()
        rr = request_api('POST', 'app/sample/save', result, token)
        print(rr.text, 'new-project')

        if rr.status_code == 401: return HttpResponse(rr.text)
        return redirect('templates')
    result = None
    all_chapters = get_all_chapters(token)
    deps = get_deps(token)
    if request.GET.get('id'):
        result = get_template(int(request.GET.get('id')), token)
        print('RESULT', result)
        result['fullTeacherName'] = f'{result["teacher"]["surname"]} {result["teacher"]["firstname"]} {result["teacher"]["lastname"]}'
        result['fullHeadTeacherName'] = f'{result["headTeacher"]["surname"]} {result["headTeacher"]["firstname"]} {result["headTeacher"]["lastname"]}'

        all_chapters.insert(0, all_chapters.pop(all_chapters.index([e for e in all_chapters if e == result['clazz']['title']][0])))
        deps.insert(0, deps.pop(deps.index([e for e in deps if e == result['department']['title']][0])))
    r = {'reg': all_chapters, 'deps': deps}
    if result: r['edit'] = result
    return render(request, 'new-project.html', r)

def get_deps(token):
    result = request_api('GET', 'extra/get-all-faculties', token=token).json()
    r = []
    for e in result[0]['departments']:
        r.append(e['title'])
    return r

def get_all_chapters(token):
    result = request_api('GET', 'extra/get-all-chapters', token=token).json()
    r = []
    for e in result:
        for clazz in e['classes']:
            r.append(clazz['title'])
    return r

def signup(request):
    if request.method == 'POST':
        if request.POST.get('login', False): return redirect('login')
        result = request_signup(request.POST)
        if result.status_code == 400: return render(request, 'signup.html', {'error': 'already'})
        elif result.status_code == 401: return render(request, 'signup.html', {'error': 'wrong'})
        data = request_login(request.POST['username'], request.POST['password'])
        response = HttpResponseRedirect('/templates')
        response.set_cookie('token', data['accessToken'])
        return response
    return render(request, 'signup.html')

def logout(request):
    response = HttpResponseRedirect('/login')
    response.set_cookie('token', '')
    return response

def files(request):
    token = request.COOKIES.get('token')
    if not is_valid(token): return redirect('/login')
    result = request_api('GET', 'app/technical_assignment/get-all', token=token).json()
    if request.method == 'POST':
        form_data  = int(request.POST['id'])
        if request.POST.get('download'):
            r = request_api('GET', 'app/technical_assignment/get-file/' + str(form_data), token=token)
            print(r.content)
            response = HttpResponse(r.content, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            response["Content-Disposition"] = f"attachment; fr.docx"
            return response
        elif request.POST.get('delete'):
            print(request_api('DELETE', 'app/technical_assignment/delete', {'technicalAssignmentId': form_data}, token).text)
            return redirect('files')
    # TODO
    result = {'templates': [{'title': e['sample']['programShortName'], 'data': e['sample']['sampleId'], 'id': e['techAssigmentId']} for e in result]}
    return render(request, 'files.html', result)

def templates(request):
    token = request.COOKIES.get('token')
    if not is_valid(token): return redirect('/login')
    result = request_api('GET', 'app/sample/get-all', token = token).json()
    if request.method == 'POST':
        form_data  = int(request.POST['id'])
        if request.POST.get('edit'):
            return redirect(reverse('new-project') + f'?id={form_data}')
        elif request.POST.get('delete'):
            request_delete('app/sample/delete', {'sampleId': form_data}, token)
            result = request_api('GET', 'app/sample/get-all', token=token).json()
        elif request.POST.get('create'):
            request_api('POST', 'app/technical_assignment/generate', {'sampleId': form_data}, token)
            return redirect('files')
    # TODO
    result = {'templates': [{'title': e['programShortName'], 'data': e['sampleId'], 'id': e['sampleId']} for e in result]}
    return render(request, 'templates.html', result)

def request_delete(api_url, data = None, token = None, base_url = 'http://158.160.13.158:8081/api/'):
    print(data, token)
    return requests.request('DELETE', base_url + api_url, json=data, headers={'Authorization': f'Bearer {token}'} if token else None)

def request_login(name, password):
    data = {
        'username': name,
        'password': password
    }
    return request_api('POST', 'auth/signin', data)

def get_clazz(clazz, token):
    result = request_api('GET', 'extra/get-all-chapters', token=token).json()
    for cc in result:
        for code in cc['classes']:
            if code['title'] == clazz:
                return code

def get_department(department, token):
    result = request_api('GET', 'extra/get-all-faculties', token=token).json()
    return [e for e in result[0]['departments'] if e['title'] == department][0]

def get_template(id, token):
    return [i for i in request_api('GET', 'app/sample/get-all', token = token).json() if i['sampleId'] == id][0]

def request_faculties(token):
    return request_api('GET', 'extra/get-all-faculties', None, token)

def request_signup(data):
    data = {
        'username': data['username'],
        'email': data['email'],
        'password': data['password'],
        'person': {
            'firstname': data['firstname'],
            'surname': data['surname'],
            'lastname': data['lastname'],
            'status': data['status']
        }
    }
    return request_api('POST', 'auth/signup', data)

def is_valid(token):
    return token is not None and request_api('GET', 'test/user', None, token).status_code != 401

def request_api(method, api_url, data = None, token = None, base_url = 'http://158.160.13.158:8081/api/'):
    return requests.request(method, base_url + api_url, json=data, headers={'Authorization': f'Bearer {token}'} if token else None)