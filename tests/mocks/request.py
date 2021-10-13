class MockRequests:
    def __init__(self, json_data=None):
        self.json_data = json_data

    def json(self):
        return self.json_data
