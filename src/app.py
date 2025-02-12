from robyn import Robyn, Request, jsonify
from os_lib.os_data_object import OSDataObject

app = Robyn(__file__)

@app.post("/features")
def get_features(request: Request):
    try:
        # Parse the request body
        body = request.json()

        # Extract collection_id and usrn from request body
        collection_id = body.get('collection_id')
        usrn = body.get('usrn')

        # Validate required fields
        if not collection_id:
            return {
                "status_code": 400,
                "headers": {"Content-Type": "application/json"},
                "description": "Bad Request",
                "data": jsonify({"error": "collection_id is required"})
            }

        # Initialise OS Data Object
        os_data = OSDataObject()

        # Get features
        if usrn:
            features = os_data.get_collection_features(
                collection_id=collection_id,
                query_attr="usrn",
                query_attr_value=usrn
            )
        else:
            features = os_data.get_collection_features(
                collection_id=collection_id
            )

        # Return successful response
        return {
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "description": "OK",
            "data": jsonify(features)
        }

    except Exception as e:
        return {
            "status_code": 500,
            "headers": {"Content-Type": "application/json"},
            "description": "Internal Server Error",
            "data": jsonify({"error": str(e)})
        }

if __name__ == "__main__":
    app.add_response_header("Server", "Robyn")
    app.start(port=8080)
