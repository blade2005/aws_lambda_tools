class DynamoDB(object):
    """DynamoDB."""

    def __init__(self, client=False):
        """Init."""
        self.client = client
        if client:
            self.dynamodb = boto3.client('dynamodb')
        else:
            session = boto3.Session()
            self.dynamodb = session.resource('dynamodb')

    def create_table(self, table, primary_key='Id', ):
        """Create table in DynamoDB"""
        table_o = self.dynamodb.create_table(
            TableName=table,
            KeySchema=[{'AttributeName': primary_key, 'KeyType': 'HASH'}],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5},
            AttributeDefinitions=[{'AttributeName': primary_key, 'AttributeType': 'S'}],
        )
        table_o.wait_until_exists()
        return table_o

    def table(self, table):
        """Return table object"""
        if self.client:
            return self.dynamodb
        else:
            return self.dynamodb.Table(table)

    def table_count(self, table):
        """Get count from Table"""
        if self.client:
            return self.dynamodb.describe_table(TableName=table)['Table']['ItemCount']
        else:
            return self.dynamodb.Table(table).item_count

    def insert(self, table, item):
        """Insert doc into DynamoDB"""
        if self.client:
            return self.dynamodb.put_item(TableName=table, Item=item)
        else:
            return self.dynamodb.Table(table).put_item(Item=item)

    def table_capacity(self, table):
        """Get table capacity"""
        old_read = old_write = None
        if self.client:
            resp = self.dynamodb.describe_table(TableName=table)
            old_read = resp['ProvisionedThroughput']['ReadCapacityUnits']
            old_write = resp['ProvisionedThroughput']['WriteCapacityUnits']
        else:
            resp = self.dynamodb.Table(table).provisioned_throughput
            old_read = resp['ReadCapacityUnits']
            old_write = resp['WriteCapacityUnits']
        return (old_read, old_write)

    def change_capacity(self, table, read, write):
        """Update table capacity"""
        data = {}
        data['ReadCapacityUnits'] = read
        data['WriteCapacityUnits'] = write
        if self.client:
            resp = self.dynamodb.update_table(TableName=table,
                                              ProvisionedThroughput=data)
        else:
            resp = self.dynamodb.Table(table).update(
                ProvisionedThroughput=data)
        while self.dynamodb.Table(table).table_status != 'ACTIVE':
            time.sleep(1)
        return resp

    def query(self, table, key, value, index=None, lastevaluatedkey=None):
        """Execute query to DynamoDB"""
        resp = None
        if lastevaluatedkey and index:
            resp = self.table(table).query(ExclusiveStartKey=lastevaluatedkey,
                                           IndexName=index,
                                           KeyConditionExpression=Key(key).eq(value))
        elif not lastevaluatedkey and index:
            resp = self.table(table).query(IndexName=index,
                                           KeyConditionExpression=Key(key).eq(value))
        elif lastevaluatedkey and not index:
            resp = self.table(table).query(ExclusiveStartKey=lastevaluatedkey,
                                           KeyConditionExpression=Key(key).eq(value))
        else:
            resp = self.table(table).query(KeyConditionExpression=Key(key).eq(value))

        if resp:
            count = resp['Count']
            results = resp['Items']
            if resp['LastEvaluatedKey']:
                n_resp, n_count = self.query(table, key, value, index, resp['LastEvaluatedKey'])
                results.extend(n_resp)
                count += n_count
            return (results, count)


    def get(self, table, key, value):
        """Get doc from specific keys"""
        resp = self.table(table).get_item(Key={key: value})
        if resp and isinstance(resp, dict) and 'Item' in resp.keys():
            return resp['Item']

    def scan(self, table, lastevaluatedkey=None):
        """Scan table for record based on key, returns all records recursively"""
        resp = None
        if lastevaluatedkey:
            resp = self.table(table).scan(ExclusiveStartKey=lastevaluatedkey)
        else:
            resp = self.table(table).scan()
        if resp:
            count = resp['Count']
            results = resp['Items']
            if resp['LastEvaluatedKey']:
                n_resp, n_count = self.scan(table, resp['LastEvaluatedKey'])
                results.extend(n_resp)
                count += n_count
            return (results, count)

