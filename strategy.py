class AlertStrategy:
    def severity(self):
        return "P3"


class RDBMSAlert(AlertStrategy):
    def severity(self):
        return "P0"


class APIAlert(AlertStrategy):
    def severity(self):
        return "P1"


class CacheAlert(AlertStrategy):
    def severity(self):
        return "P2"


def get_alert_strategy(component_id: str):
    if "RDBMS" in component_id:
        return RDBMSAlert()
    if "API" in component_id:
        return APIAlert()
    if "CACHE" in component_id:
        return CacheAlert()
    return AlertStrategy() 
