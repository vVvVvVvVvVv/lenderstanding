from functools import wraps
from flask import Flask, render_template, request, jsonify, Response
from app import app, host, port, user, passwd, db
from app.helpers.database import con_db
import pymysql as MySQLdb
import pickle
import numpy as np
import dateutil.parser
import csv
import math
import random

# Define helper functions
from app.helpers.database import con_db, query_db
from app.helpers.filters import format_currency
import jinja2

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == 'guest' and password == 'insight123'

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

#Change sql to 0.0.0.0
def sqlExec(query):
    con = MySQLdb.connect(user=user, host=host, port=port, passwd=passwd, db=db)
    with con:
        cur = con.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(query)
        tables = cur.fetchall()
        return tables

def remove_uni(s):
    """remove the leading unicode designator from a string"""
    if isinstance(s, unicode):
        s = s.encode("ascii", "ignore")
    return s

@app.route("/")
@requires_auth
def hello():
    return render_template('index.html')
#ifexists = 0
#while ifexists ==0:
#    rand_loanid = random.randint(0, 5000)
#    cnt=sqlExec("SELECT COUNT(1) AS total FROM loanapplic WHERE loanid = %d;" % rand_loanid)
#    ifexists = int(cnt[0]['total'])

@app.route('/index.html')
def index():
    return render_template('index.html')    

@app.route("/about.html")
def aboutfn():
    return render_template('about.html')

@app.route("/search.html")
@requires_auth
def search():
    user   = app.config["DATABASE_USER"]
    host   = app.config["DATABASE_HOST"]
    port   = app.config["DATABASE_PORT"]
    passwd = app.config["DATABASE_PASSWORD"]
    db     = app.config["DATABASE_DB"]
    
    # Need to change this on AWS:
    con = MySQLdb.connect(user=user, host=host, port=port, passwd = passwd, db=db)
    cursor = con.cursor()

    # Loan ID
    loan_id = int(request.args.get("loan_id", None))
    pickle.dump( loan_id, open( "passloan.pkl", "wb"))

    # Load loan info
    loan_info = sqlExec("SELECT borrowerid, sift_score, interest, period, length(family_member1_mobile_phone) as family1, applydate-borrowers.Created as time_to_complete, length(frontNationalId) as fnid,firstname as first, reffered_by as referred_by, Country as country, City as city, Amount as amount, loanuse from loanapplic join borrowers on loanapplic.borrowerid = borrowers.userid join borrowers_extn on borrowers_extn.userid = borrowers.userid where loanid = %d;" % loan_id)
    print loan_info[0]['loanuse']
    loan_info[0]['loanuse'] = loan_info[0]['loanuse'].decode("ascii", "ignore")

    # Sift score
    sift_score       = loan_info[0]['sift_score']
    interest         = loan_info[0]['interest']
    period           = loan_info[0]['period']
    family1          = loan_info[0]['family1']
    fnid             = loan_info[0]['fnid']
    time_to_complete = loan_info[0]['time_to_complete']
    interest         = loan_info[0]['interest']
    
    # Check for null values 
    if family1 is None:
        family1 = 0
    if fnid is None:
        fnid = 0
    
    # Features
    xin = np.array([sift_score, time_to_complete, interest, period, family1, fnid])

    # Load model - Lin regression
    clf = pickle.load(open('app/helpers/model.pkl', "rb"))
    y = clf.predict(xin)[0]
    prob_default = 100.0*clf.predict_proba(xin)[0][1]
    
    # Make prediction
    if y == 0:
        ypred = 'Will pay back loan in full'
    elif y ==1:
        ypred = 'Will default'
    
    # Set image id file
    image_id_str = "static/images/loan_images/" + str(loan_id) + ".jpg"
    return render_template('search.html', loan_id=loan_id, loan_info=loan_info, y=y, ypred=ypred, prob_default=prob_default, image_id_str =image_id_str)

@app.route("/blocker")
def block():
    return "Blocked!"

@app.route('/<pagename>')
def regularpage(pagename = None):
    """
        Route not found by the other routes above.
        """
    return "You've arrived at : " + pagename
