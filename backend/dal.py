import psycopg2
import log
from config import dbConfig
from utils import protocol
import model

HOST = dbConfig['host'].strip()
NAME = dbConfig['name'].strip()
USER = dbConfig['user'].strip()
PASS = dbConfig['pass'].strip()

def setup_conn(host,name,user,password):
    if name != None:
        conn_string = "host='{}' dbname='{}' user='{}' password='{}'".format(host,name,user,password)
    else:
        conn_string = "host='{}' user='{}' password='{}'".format(host,user,password)
    conn = psycopg2.connect(conn_string)
    conn.autocommit = True
    log.info("Succesfully connected to DB {}/{} with user {}".format(host,str(name),user))
    return conn

#Set up analytics db connection
try:
    conn = setup_conn(HOST,NAME,USER,PASS)
except:
    log.critical("Unable to connect to the DB")


#QUERY BUILDERS
def match_analyses_sql(tags):
    formatted_tags = str(tags).replace("'", '"')
    q="""
        SELECT anly.analysis_id, anly.tags, anly.payload, anly.status
        FROM (
            SELECT at.analysis_id, count(*) AS cnt
            FROM (
                -- create table from analysis table with one tag per row
                SELECT json_array_elements(tags) AS tag, analysis_id FROM analyses
                ) at
            -- create table from input with one tag per row and join
            INNER JOIN (SELECT json_array_elements('{tags}') AS tag
            ) it
            ON ((at.tag->>'measure' = it.tag->>'measure') or (at.tag->>'dimension' = it.tag->>'dimension'))
            GROUP BY at.analysis_id
        ) matched_tags
        -- join back to analysis jobs table to get the payload and status (cannot group by payload as it is JSON)
        INNER JOIN analyses anly ON anly.analysis_id = matched_tags.analysis_id
        ORDER BY matched_tags.cnt DESC
        LIMIT 100;
    """
    query = q.format(tags=formatted_tags)
    return query

def insert_new_analysis_sql(tags, sentence):
    formatted_tags = str(tags).replace("'", '"')
    print tags
    print sentence
    q="""
        INSERT INTO analyses
        VALUES (DEFAULT, '{tags}', '{{"query":"{sentence}"}}', 'queued');
    """
    query = q.format(tags=formatted_tags, sentence=sentence)
    return query

#HELPERS

#Cursor builder. By default get global connection to analytics db
def db(c = conn):
    return c.cursor()

def query(sql):
    log.debug("Executing query in host:{} -> {}".format(HOST,sql))
    return sql

def escapeForSql(value):
    if type(value) == str or type(value) == unicode:
        return "\'" + value.strip() + "\'"
    else:
        log.debug("Not escaping value with type " + str(type(value)))
        return str(value)


#QUERIES
def select_analysis_by_id(analysis_id):
    sql = '''SELECT * from analyses where analysis_id = {}'''.format(analysis_id)
    cursor = db()
    cursor.execute(sql)
    return model.Analysis(cursor.fetchone())

def queue_analysis(sentence, tags):
    try:
        db().execute(query(insert_new_analysis_sql(tags,sentence)))
        log.info("Successfully appended new analysis to queue")
        return { 'status' : 'OK' }
    except Exception as e:
        return protocol.error(e)

def query_analyses(tags):
    try:
        if type(tags) is not list:
            raise AssertionError("Tags must be a list!")
        cursor = db()
        cursor.execute(query(match_analyses_sql(tags)))
        msg = "Succesfully extracted analyses"
        i = cursor.fetchall()
        print i
        items = [model.Analysis(proto).toDict() for proto in i]
        return protocol.success(msg,items)
    except Exception as e:
        return protocol.error(e)

def update_analysis(uid,params):
    try:
        _sql = ""
        for key in params:
            if key == 'analysis_id':
                continue
            _sql = _sql + str(key) + " = " + escapeForSql(params[key]) + ","
        sql = query("UPDATE analyses SET " + _sql[:-1] + " WHERE analysis_id = " + str(uid) +";")
        cursor = db()
        cursor.execute(sql)
        return protocol.success("Successfully updated analysis with id "+str(uid), cursor.statusmessage)
    except Exception as e:
        return protocol.error(e)


def new_analysis(source_id,dimensions,metric,query):
    source_id = source_id
    dimensions = dimensions
    measures = metric
    sentence = query
    tags = []
    for item in dimensions:
        tags.append({"dimension": item})
    tags.append({"measure": metric})

    formatted_tags = str(tags).replace("'", '"')
    q="""
        INSERT INTO analyses
        VALUES (DEFAULT, '{tags}', '{{"source_id":"{source_id}","query":"{sentence}"}}', 'available');
    """
    sql = q.format(tags=formatted_tags, source_id=source_id, sentence=sentence)
    uid = db().execute(sql)
    return protocol.success("Successfully created analysis with id "+str(uid))

def select_source_by_id(sid):
    sql = '''SELECT * from data_sources where sid = {}'''.format(sid)
    cursor = db()
    cursor.execute(sql)
    return model.DataSource(cursor.fetchone())

def get_sources():
    try:
        sql = query("SELECT * from data_sources;")
        cursor = db()
        cursor.execute(sql)
        items = [model.DataSource(proto).toDict() for proto in cursor.fetchall()]
        return protocol.success("Successfully fetched data sources",items)
    except Exception as e:
        return protocol.error(e)

def create_source(type_of,host,port,user,password):
    try:
        sql = query("""INSERT INTO data_sources
            VALUES (DEFAULT,'{}', '{}', {}, '{}', '{}')
            RETURNING sid""".format(type_of,host,str(port),user,password))
        cursor = db()
        cursor.execute(sql)
        uid = cursor.fetchone()
        return protocol.success("Successfully created new source with id "+str(uid), cursor.statusmessage)
    except Exception as e:
        return protocol.error(e)

def update_source(uid,params):
    try:
        _sql = ""
        for key in params:
            if key == 'sid':
                continue
            _sql = _sql + str(key) + "=" + escapeForSql(params[key]) + ","
        sql = query("UPDATE data_sources SET " + _sql[:-1] + " WHERE sid = " + str(uid) +";")
        cursor = db()
        cursor.execute(sql)
        if cursor.rowcount == 1:
            return protocol.success("Successfully updated source with id " + str(uid),cursor.statusmessage)
        else:
            return protocol.warning("Could not update data source with id "+str(uid))
    except Exception as e:
        return protocol.error(e)

def delete_source(uid):
    try:
        sql = query("DELETE from data_sources where sid ={id};".format(id=uid))
        cursor = db()
        cursor.execute(sql)
        if cursor.rowcount == 1:
            return protocol.success("Succesfully deleted data source with id " +str(uid),cursor.statusmessage)
        else:
            return protocol.warning("Could not delete data source with id "+str(uid))
    except Exception as e:
        return protocol.error(e)


def run_query(analysis_id):
    try:
        analysis = select_analysis_by_id(analysis_id)
        query = analysis.payload['query']
        source = select_source_by_id(analysis.payload['source_id'])

        if source.type.lower() == 'psql':
            conn = setup_conn(source.host,None,source.username,source.password)
            cursor = db(conn)
            cursor.execute(query)
            items = cursor.fetchall()
            return protocol.success("Succesfully executed query with id "+str(analysis_id),items)

        elif source.type.lower() == 'mysql':
            protocol.warning("Not implemented!")

        elif source.type.lower() == 'hive':
            protocol.warning("Not implemented!")

    except Exception as e:
        return protocol.error(e)




