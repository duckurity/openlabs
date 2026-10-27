"""Public API description. Contains shapes and workflows, not runtime secrets."""


def obj(properties, required=None):
    return {'type': 'object', 'properties': properties, 'required': list(properties) if required is None else required, 'additionalProperties': False}


def ref(name):
    return {'$ref': '#/components/schemas/' + name}


def array(value):
    return {'type': 'array', 'items': value}


def document():
    text = {'type': 'string'}
    integer = {'type': 'integer'}
    email = {'type': 'string', 'format': 'email', 'maxLength': 254,
             'description': 'Use a fictional address ending in .test.'}
    reset_target_email = {**email, 'description': 'Email address of the account whose password is updated.'}
    password = {'type': 'string', 'format': 'password', 'minLength': 10, 'maxLength': 128}
    reset_code = {'type': 'string', 'minLength': 1, 'maxLength': 128}
    schemas = {
        'Error': obj({'error': text}),
        'Message': obj({'message': text}),
        'User': obj({'id': integer, 'name': text, 'email': email, 'role': {'type': 'string', 'enum': ['customer', 'courier']}}),
        'Session': obj({'token': text, 'user': ref('User')}),
        'Locker': obj({'id': text, 'name': text, 'district': text, 'status': {'type': 'string', 'enum': ['available', 'in_transit', 'held']}, 'parcels': integer, 'capacity': integer}),
        'Event': obj({'time': {'type': 'string', 'format': 'date-time'}, 'text': text}),
        'Courier': obj({'name': text, 'email': email}),
        'Mail': obj({'id': integer, 'subject': text, 'body': text, 'code': text, 'created_at': {'type': 'string', 'format': 'date-time'}}),
        'RouteLocker': obj({'id': text, 'name': text, 'status': text}),
        'Manifest': obj({'locker_id': text, 'reference': text, 'recipient': text, 'contents': text, 'release_flag': text}),
        'Empty': obj({}),
        'Register': obj({'name': {'type': 'string', 'minLength': 1, 'maxLength': 80}, 'email': email, 'password': password}),
        'Login': obj({'email': email, 'password': password}),
        'ResetRequest': obj({'email': email}),
        'ResetConfirm': obj({'email': reset_target_email, 'code': reset_code, 'new_password': password}),
    }
    schemas['LockerDetail'] = obj({**schemas['Locker']['properties'], 'address': text, 'updated_at': {'type': 'string', 'format': 'date-time'}, 'events': array(ref('Event'))})
    schemas['Route'] = obj({'id': text, 'name': text, 'dispatch_note': text, 'lockers': array(ref('RouteLocker'))})
    schemas['Dashboard'] = obj({'checkpoint_flag': text, 'courier': ref('Courier'), 'summary': obj({'assigned_lockers': integer, 'held': integer})})

    def operation(summary, response, *, authenticated=False, request_schema=None, status='200', courier=False):
        result = {'summary': summary, 'security': [{'bearerAuth': []}] if authenticated else [],
                  'responses': {status: {'description': 'Success', 'content': {'application/json': {'schema': response}}},
                                '400': {'description': 'Invalid input', 'content': {'application/json': {'schema': ref('Error')}}}}}
        if authenticated:
            result['responses']['401'] = {'description': 'Missing or expired bearer token', 'content': {'application/json': {'schema': ref('Error')}}}
        if courier:
            result['description'] = 'Requires a courier session. Locker actions are restricted to the assigned courier.'
            result['responses']['403'] = {'description': 'Courier role required', 'content': {'application/json': {'schema': ref('Error')}}}
        if request_schema:
            result['requestBody'] = {'required': True, 'content': {'application/json': {'schema': ref(request_schema)}}}
        return result

    paths = {
        '/api/lockers': {'get': operation('List locker-bank status', obj({'lockers': array(ref('Locker'))}))},
        '/api/lockers/{locker_id}': {'get': operation('Read public locker status and event history', obj({'locker': ref('LockerDetail')}))},
        '/api/auth/register': {'post': operation('Create a customer account', ref('Session'), request_schema='Register', status='201')},
        '/api/auth/login': {'post': operation('Sign in', ref('Session'), request_schema='Login')},
        '/api/auth/logout': {'post': operation('Revoke the current session', obj({'ok': {'type': 'boolean'}}), authenticated=True)},
        '/api/me': {'get': operation('Read your account', obj({'user': ref('User')}), authenticated=True)},
        '/api/auth/reset/request': {'post': operation('Send a code to your lab mailbox', ref('Message'), authenticated=True, request_schema='ResetRequest')},
        '/api/auth/reset/confirm': {'post': operation('Confirm a password update', ref('Message'), authenticated=True, request_schema='ResetConfirm')},
        '/api/mailbox': {'get': operation('Read your lab mailbox', obj({'messages': array(ref('Mail'))}), authenticated=True)},
        '/api/courier/dashboard': {'get': operation('Read courier dispatch summary', ref('Dashboard'), authenticated=True, courier=True)},
        '/api/courier/routes': {'get': operation('List assigned courier routes', obj({'routes': array(ref('Route'))}), authenticated=True, courier=True)},
        '/api/courier/lockers/{locker_id}/open': {'post': operation('Release a held manifest', obj({'manifest': ref('Manifest')}), authenticated=True, courier=True, request_schema='Empty')},
    }
    for path, methods in paths.items():
        if '{locker_id}' in path:
            for operation_data in methods.values():
                operation_data['parameters'] = [{'name': 'locker_id', 'in': 'path', 'required': True, 'schema': text}]
                operation_data['responses']['404'] = {'description': 'No accessible locker or manifest', 'content': {'application/json': {'schema': ref('Error')}}}
    paths['/api/courier/lockers/{locker_id}/open']['post']['responses']['409'] = {'description': 'Locker has no held release manifest', 'content': {'application/json': {'schema': ref('Error')}}}
    paths['/api/auth/register']['post']['responses']['409'] = {'description': 'Account already exists', 'content': {'application/json': {'schema': ref('Error')}}}
    paths['/api/auth/login']['post']['responses']['401'] = {'description': 'Invalid credentials', 'content': {'application/json': {'schema': ref('Error')}}}
    paths['/api/auth/reset/confirm']['post']['responses']['404'] = {'description': 'Email is not registered; the code stays valid', 'content': {'application/json': {'schema': ref('Error')}}}
    return {'openapi': '3.0.3', 'info': {'title': 'ParcelPoint dispatch API', 'version': '1.0.0', 'description': 'Fictional local parcel-locker network. All state is disposable. Password reset codes arrive in the signed-in account mailbox and expire after ten minutes.'},
            'servers': [{'url': '/'}], 'paths': paths,
            'components': {'schemas': schemas, 'securitySchemes': {'bearerAuth': {'type': 'http', 'scheme': 'bearer'}}}}
