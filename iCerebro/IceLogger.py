import logging


class IceLogger:
    def __init__(self, username):
        self.logger = logging.getLogger('console')
        self.extra = {'bot_username': username}

    def critical(self, msj):
        # print(msj)
        self.logger.critical(msj, extra=self.extra)

    def error(self, msj):
        # print(msj)
        self.logger.error(msj, extra=self.extra)

    def warning(self, msj):
        # print(msj)
        self.logger.warning(msj, extra=self.extra)

    def info(self, msj):
        # print(msj)
        self.logger.info(msj, extra=self.extra)

    def debug(self, msj):
        # print(msj)
        self.logger.debug(msj, extra=self.extra)
