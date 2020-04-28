from locust import HttpLocust, TaskSet, task, events
import datetime

class ElbTasks(TaskSet):
  @task(1)
  def status(self):
      start = datetime.datetime.now()
      response = self.client.get("/sign-in")
      end = datetime.datetime.now()
      if response.status_code == 200:
        events.request_success.fire(request_type="http", name="success", response_time=(end-start), response_length=len(response.text))
      else:
        events.request_success.fire(request_type="http", name="failure", response_time=(end-start), response_length=len(response.text))

class ElbWarmer(HttpLocust):
  task_set = ElbTasks
