def handler(event, context):
    return {"sum": sum(i * i for i in range(200_000))}
