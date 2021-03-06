from flask import Flask, request, abort, jsonify, make_response
import parser
from flask import render_template
import log
import dal

app = Flask(__name__)

base_url = '/api/v1.0'

@app.route('/')
def hello(name=None):
    return render_template('index.html')

#adhered to utils.protocol
def responsify(output):
    status = output['status']
    if status == 'error':
        return make_response(jsonify(output), 500)
    if status == 'warn':
        return make_response(jsonify(output), 400)
    else:
        if 'result' in output:
            return make_response(jsonify({ 'content' : output['result'] }), 200)
        else:
            return make_response(jsonify({'content' : 'ok'}), 200)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.errorhandler(400)
def missing(error):
    return make_response(jsonify({'error': 'Something is missing'}), 400)

@app.errorhandler(500)
def internal_server_error(error):
    return make_response(jsonify({'error': 'Oops! Something went wrong!'}), 500)


@app.route(base_url+"/analysis", methods=['POST','GET'])
def analyses():

    if request.method == 'GET':
        print request.args
        sentence = request.args['request']
        tags = parser.parse_request(sentence)
        analyses = dal.query_analyses(tags)
        return responsify(analyses)

    if request.method == 'POST':
        try:
            sentence = request.json['request']
            tags = parser.parse_request(sentence)
            result = dal.queue_analysis(sentence,tags)
            return responsify(result)
        except Exception as e:
            log.error(e)
            abort(400)


@app.route(base_url+"/query", methods=['POST'])
def query():
    if not request.json or not 'analysis_id' in request.json:
        abort(400)
        pass
    query = request.json['analysis_id']
    result = dal.run_query(query)
    return responsify(result)


#ADMIN CONSOLE

@app.route(base_url+"/admin/source", methods=['POST','PUT', 'DELETE', 'GET'])
def sources():
    if request.method == 'PUT':
        try:
            source = request.json['source']
            result = dal.update_source(source['sid'],source)
            return responsify(result)
        except Exception as e:
            log.warn(e)
            abort(400)

    if request.method == 'POST':
        try:
            source = request.json['source']
            host = source['host']
            user = source['username']
            password = source['password']
            type_of = source['type']
            port = source['port']
            result = dal.create_source(type_of,host,port,user,password)
            return responsify(result)
        except Exception as e:
            log.warn(e)
            abort(400)

    if request.method == 'GET':
        try:
            result = dal.get_sources()
            return responsify(result)
        except Exception as e:
            log.warn(e)
            abort(400)

    if request.method == "DELETE":
        try:
            source = request.json['source']
            uid = source['sid']
            result = dal.delete_source(uid)
            return responsify(result)
        except Exception as e:
            log.warn(e)
            abort(400)


@app.route(base_url+"/admin/analysis", methods=['POST', 'PUT'])
def admin_analysis():
    if not request.json:
        abort(400)

    if request.method == 'POST':
        try:
            analysis = request.json['analysis']
            source_id = analysis['source_id']
            dimensions = analysis['dimensions']
            metric = analysis['metric']
            query = analysis['query']
            result = dal.new_analysis(source_id,dimensions,metric,query)
            return responsify(result)
        except Exception as e:
            log.warn(e)
            abort(400)

    if request.method == 'PUT':
        try:
            analysis = request.json['analysis']
            uid = analysis['analysis_id']
            result = dal.update_analysis(uid,analysis)
            return responsify(result)
        except Exception as e:
            log.warn(e)
            abort(400)



