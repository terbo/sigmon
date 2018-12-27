from flask import Flask
from pid import PidFile
mypid = PidFile(piddir='/tmp')

app = Flask(__name__)

import views
