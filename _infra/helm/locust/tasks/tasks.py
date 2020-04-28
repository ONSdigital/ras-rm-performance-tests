from locust import HttpLocust, TaskSet, task, events, between
import datetime

class ElbTasks(TaskSet):
  @task(1)
  def status(self):
      response = self.client.get("/sign-in")

class ElbWarmer(HttpLocust):
  task_set = ElbTasks
  wait_time = between(5, 15)