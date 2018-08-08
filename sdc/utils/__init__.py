import os
import time

polling_wait_time = int(os.getenv('POLLING_WAIT_TIME', '2'))
polling_retries = int(os.getenv('POLLING_RETRIES', '30'))


def wait_for(action):
    count = 0
    result = action()
    while not result:
        count += 1
        if count >= polling_retries:
            raise BaseException(
                f'Operation timed out after {polling_retries} retries.')

        time.sleep(polling_wait_time)
        result = action()

    return result
