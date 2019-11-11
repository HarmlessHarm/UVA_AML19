from __future__ import print_function
import os
import sys
import json
import requests
import shutil
import numpy as np
import hashlib

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = OSError


class ServerError(BaseException):
    pass


class Config:
    host = 'http://18.184.150.76:1234/'
    cwd = os.path.dirname(os.path.realpath(__file__))
    test_folder = os.path.join(cwd, 'local_tests')
    test_path = os.path.join(test_folder, 'tests.pickle')


# Local tests
def _remove_local_tests():
    try:
        os.remove(Config.test_path)
        print('Current version of local tests is deprecated. Outdated tests are removed.')
        sys.stdout.flush()
    except FileNotFoundError:
        pass


def _load_local_tests(username):
    if not os.path.exists(Config.test_folder):
        os.makedirs(Config.test_folder)

    try:
        endpoint = Config.host + 'load_tests/{}'.format(username)
        stream = requests.get(endpoint, stream=True)
        if stream.status_code == 200:
            with open(Config.test_path, 'wb') as f:
                stream.raw.decode_content = True
                shutil.copyfileobj(stream.raw, f)
            print('Local tests are downloaded.')
            sys.stdout.flush()
        else:
            error = stream.json()['error']
            raise ServerError(error)
    except ServerError as e:
        raise e
    except:
        raise ServerError('Error downloading local tests.')


def _local_tests_are_valid():
    try:
        hash_md5 = hashlib.md5()
        with open(Config.test_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        local_md5 = hash_md5.hexdigest()
        endpoint = Config.host + 'check_sum/{}'.format(local_md5)
        response = requests.get(endpoint).json()
        return response['success']
    except:
        return False


def _passed_local_tests(function, arg_keys):
    with open(Config.test_path, 'rb') as f:
        try:
            test_data = pickle.load(f, encoding='latin1')
        except TypeError:
            test_data = pickle.load(f)

    data = test_data[function.__name__]
    inputs = data['inputs']
    outputs = data['outputs']

    for in_, out_ in zip(inputs, outputs):
        args_ = {k: in_[k] for k in arg_keys}
        answer = function(**args_)
        if not np.allclose(answer, out_, rtol=1e-5, atol=1e-5):
            return False
    return True


# Remote tests
def _passed_remote_test(username, function, arg_keys):
    endpoint = Config.host + 'get_test_input/{}/{}'.format(username, function.__name__)
    response = requests.get(endpoint)
    data = response.json()

    if 'error' in data:
        raise ServerError(data['error'])

    args = []
    for key in arg_keys:
        arg_ = data['input'][key]
        arg_value = data['input'][key]['data']
        if arg_['type'] == 'ndarray':
            arg_value = np.array(arg_value)
        args.append(arg_value)

    test_result = function(*args)
    test_result = np.array(test_result).tolist()
    endpoint = Config.host
    endpoint += 'check_answer/{}/{}/{}/{}'.format(username, function.__name__,
                                                  data['ipd'], json.dumps(test_result))

    response = requests.get(endpoint)
    if not response.status_code == 200:
        raise ServerError('Internal Error Occurred')
    answer_response = response.json()

    return answer_response['success']


def get_progress(username):
    endpoint = Config.host + 'get_progress/{}'.format(username)
    response = requests.get(endpoint)
    data = response.json()

    if 'error' in data:
        raise ServerError(data['error'])

    print('-'*45)
    print('| {:42}|'.format(data['name']))
    print('| {:42}|'.format(data['mail']))
    print('-'*45)
    for k, v in sorted(data['progress'].items()):
        print('| {:25}| {:15}|'.format(k, v))
    print('-'*45)


def test_student_function(username, function, arg_keys):
    if not _local_tests_are_valid():
        _remove_local_tests()
        print('Downloading local tests...')
        _load_local_tests(username)

    print('Running local tests...')
    if _passed_local_tests(function, arg_keys):
        print('{} successfully passed local tests'.format(function.__name__))
        print('Running remote test...')
        sys.stdout.flush()

        if _passed_remote_test(username, function, arg_keys):
            print("Test was successful. Congratulations!")
        else:
            print("Test failed. Please review your code.")
    else:
        print('{} failed some local tests'.format(function.__name__))
