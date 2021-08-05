import logging

def get_logger(appName='Application', handlerType='StreamHandler', \
    loggerLevel='INFO', handlerLevel='DEBUG'):
    # Creating the logger object
    log = logging.getLogger(appName)
    log.setLevel(getattr(logging, loggerLevel))

    # Initializing logging settings in handler
    handler = getattr(logging, handlerType)()
    handler.setLevel(getattr(logging, handlerLevel))
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    # binding the handler to Logger object
    log.addHandler(handler)

    return log