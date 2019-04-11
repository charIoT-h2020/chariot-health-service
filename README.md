# CharIoT Health Service

[![Foo](https://img.shields.io/badge/License-EPL-green.svg)](https://opensource.org/licenses/EPL-1.0)

This service checks periodical if all components are working. We expect
by each service to has a dedicated endpoint to collect running information.

The following diagram show how health check works with Southbound Dispatcher, it sends a health check message with MQTT, the Southbound Dispatcher when receives this message it checks for all its dependencies their health and return the result back to the health service via the MQTT broker.

```mermaid
sequenceDiagram
    participant A as Health Check
    participant J as Southbound Dispatcher
    participant D as Cloudant
    participant E as InfluxDB
    participant F as MongoDB

    loop Every minute
        A-x+J: Are you OK?
    end

    J->>D: Can connect?
    D-->>J: Connection result
    J->>E: Can connect?
    E->>J: Connection result

    J-xA: Health check response
    A->>E: Save health check response
    A->>-F: Save health info for a service
```

## Models

### Health Request

```json
{
    "id": "<unique-guid>", 
    "destination": "health/_callback", 
    "timestamp": "2019-04-04T13:12:42.531931"
}
```

id
: A unique id for the specific health check request.

destination
: Where you expecting your answer.

timestamp
: When you sent the request.

### Health Response

```json
{
    "id": "<unique-guid>", 
    "name": "southbound-dispatcher", 
    "status": {
        "code": 0, 
        "message": "running"
    }, 
    "received": "2019-04-04T13:13:11.883693", 
    "sended": "2019-04-04T13:12:42.531931"
}
```

id
: A unique id for the specific health check request.

name
: A unique name of the service.    

status.code
: Status code of running state, 0 for all are ok otherwise the service had running issues.

status.message
: A message of health state of the service.

destination
: Where you expecting your answer.

received
: When the service received your request.

received
: When you sent the request.

## Configuration

```json
{
    ...
    "health": {
        "listen": "health/#",
        "interval": 60,
        "services": [
            {
                "protocol": "mqtt",
                "name": "southbound-dispatcher",
                "endpoint": "dispatcher/_health"
            }
        ]
    },
    ...
}
```