import logging
import logging.handlers
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders

def setup_logging(log_name="85home.log"):
    """
    Setup logging configuration with daily rotation and maximum 10 log files.
    Creates logs directory if it doesn't exist.
    """
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Configure logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with daily rotation
    log_file = os.path.join(logs_dir, log_name)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name):
    """
    Get a logger instance with the specified name.
    """
    return logging.getLogger(name) 

def send_email(tiitle, content):
    toes = ["lovetoamtoboy@gmail.com","zhangzirao0219@gmail.com"]
    for toe in toes:
        send_single_email(tiitle, toe, content)

def send_single_email(title, toe, content):
    msg = MIMEMultipart()
    msg['Subject'] = "把握: %s" % reason
    frome = "lovetoamtoboy@gmail.com"
    msg['From'] = frome
    msg['To'] = toe
    msg.attach(MIMEText(content))

    try:
        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.ehlo()
        s.starttls()
        password = "lxqzrzdvgjpjlqlj"
        s.login(frome, password)
        s.sendmail(frome, toe, msg.as_string())
        s.close()
    except:
        logger = logging.getLogger()
        logger.debug("email send failed")
        pass