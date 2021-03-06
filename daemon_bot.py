#!/usr/bin/env python
import os
import time
import redis
import pickle


if 'REDIS_HOST' in os.environ:
    redis_connection = redis.Redis(host=os.environ['REDIS_HOST'], port=os.environ.get('REDIS_PORT', 6379))
else:
    redis_connection = redis.from_url(os.environ['REDIS_URL'])


def queue_daemon(queue, rv_ttl=500):
    from application import application

    while 1:
        print('[daemon]: waiting for instruction...')
        msg = redis_connection.blpop(queue)
        print('[daemon]: received!')
        try:
            func, key, args, kwargs = pickle.loads(msg[1])
        except Exception as e:
            try:
                print(f'[daemon]: failed to unpickle {e}')
            except (TypeError, IndexError):
                pass
        else:
            try:
                print(f'[daemon]: calling {func.__name__}')
                with application.app_context():
                    rv = func(*args, **kwargs)
                    print('[daemon]: complete!')
            except Exception as e:
                print(f'[daemon]: {e}')
                rv = e
            if rv is not None:
                redis_connection.set(key, pickle.dumps(rv))
                redis_connection.expire(key, rv_ttl)
                print(f'[daemon]: stored return value at {key}')
        print('[daemon]: sleeping for a bit...')
        time.sleep(0.25)


queue_daemon('deferred_queue')