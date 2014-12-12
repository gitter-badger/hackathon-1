
class Analysis(object):

    def __init__(self,t):
        if type(t) != tuple:
            raise AttributeError("Failed to init Analysis, parameter is not tuple")
        self.id = t[0]
        self.tags = t[1]
        self.payload = t[2]
        self.status = t[3]

    def __getattr__(self, attr):
         return self[attr]

    def __getitem__(self, item):
        return self.__dict__[item]



class DataSource(object):

    def __init__(self,t):
        if type(t) != tuple:
            raise AttributeError("Failed to init DataSource, parameter is not tuple")
        self.id = t[0]
        self.type = t[1]
        self.host = t[2]
        self.port = t[3]
        self.username = t[4]
        self.password = t[5]

    def __getattr__(self, attr):
         return self[attr]

    def __getitem__(self, item):
        return self.__dict__[item]

