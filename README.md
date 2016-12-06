# jeeves
Make an instant server-client out of any Python API

A sample python API is provided to demonstrate how this might be used (it's a bad example, bear with me). By running
    python jeeves.py sample_api
we instantly get a client and server. The client shares an identical interface to the original python module, but now
makes all of its calls to the server rather than running the computation directly. The server now runs Flask to receive
the REST calls and forward those calls to your original Python script, where they are executed and the results returned
back to the client. This allows for quickly peeling programs apart onto multiple machines, perhaps for load balancing,
division of labor, asynchronous programming, or cloud deployment.

There's a lot of work to be done, but for basic Python modules consisting of just regular methods (generators aren't
yet supported, and asynchronous functions aren't yet tested), it seems to be working. Of course, pickle'able arguments
are assumed to all such functions, but otherwise using the generated client and server should be virtually transparent.

Errors are pickled and re-raised client-side, so you shouldn't miss out if a regular error is raised.

Load balancing can be accomplished by putting a proxy server between the clients and servers.

TODO (not necessarily in order):
  - Support generator functions
  - Test generator functions, asynchronous functions, and more complex signatures
  - Improve configurability
  - Support classes and global variable retrieval (return values for anything that's not a function)
  - Cache results where possible
  - Implement no-file version (just execute the server directly without saving its file, and reach client via Jeeves object)
  - Improve performance
  - Reduce size of produced code (no need to duplicate boilerplate crap in Python)
  - Improve command-line arguments
