from vaxos.vaxos_app import server as application
from vaxos.settings import settings

if __name__ == '__main__':
    application.run(debug = settings.get('debug') if settings.get('debug') is not None else True,
                    host='0.0.0.0',
                    port=8050)
