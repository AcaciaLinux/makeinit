import os
import inspect

HEADER = '\033[95m'
NORMAL = '\033[94m'
OKCYAN = '\033[96m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'

# used to determine if logger is running inside docker
NO_TERM = True

def initialize():
    if("TERM" in os.environ):
        global NO_TERM
        NO_TERM = False
    else:
        print("No terminal available. Disabling log color.")
    
def warn(log):
    global NO_TERM

    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0]).__name__

    if(NO_TERM):
        print("[{}] ==> [WARN] {} ".format(module, log))
    else:
        print("{}{:<8}{}{}{:<24}{} {}".format(BOLD, "[WARN]", ENDC, WARNING, module, ENDC, log))

def error(log):
    global NO_TERM

    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0]).__name__

    if(NO_TERM):
        print("[{}] ==> [ERROR] {} ".format(module, log))
    else:
        print("{}{:<8}{}{}{:<24}{} {}".format(BOLD, "[ERROR]", ENDC, FAIL, module, ENDC, log))

def info(log):
    global NO_TERM
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0]).__name__


    if(NO_TERM):
        print("[{}] ==> {} ".format(module, log))
    else:
        print("{}{:<8}{}{}{:<24}{} {}".format(BOLD, "[INFO]", ENDC, OKGREEN, module, ENDC, log))

def web_log(log):
    global NO_TERM 

    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0]).__name__

    if(NO_TERM):
        print("[{}] -> {} ".format(module, log))
    else:
        print("{}{:<8}{}{}{:<24}{} {}".format(BOLD, "[WEB]", ENDC, OKCYAN, module, ENDC, log))

def debug(log):
    global NO_TERM

    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0]).__name__

    if(NO_TERM):
        print("[{}] ==> [DEBUG] {} ".format(module, log))
    else:
        print("{}{:<8}{}{}{:<24}{} {}".format(BOLD, "[DEBUG]", ENDC, OKCYAN, module, ENDC, log))
