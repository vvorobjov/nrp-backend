This is the implementation of the REST Backend of the Neuro Robotics Platform.

REST stack: Flask 3.x + Werkzeug 3.x with Flask-Smorest (flask.views.MethodView
blueprints and marshmallow schemas). The unmaintained Flask-RESTful was retired
under EBR2-65.

Endpoints (paths, methods and payloads unchanged by the migration):
  POST /simulation                     create a simulation
  GET  /simulation                     list simulations
  GET  /simulation/<sim_id>            get a simulation
  GET  /simulation/<sim_id>/state      get the simulation state
  PUT  /simulation/<sim_id>/state      set the simulation state
  GET  /version                        component versions (unauthenticated; used
                                       by the container HEALTHCHECK)
