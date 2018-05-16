class UnicodeDictWriter(object):
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, csvfile, fieldnames, restval='', extrasaction='raise', dialect=csv.excel, encoding="utf-8", *args, **kwds):
        # Redirect output to a queue
        self.fieldnames = fieldnames
        self.restval = restval          # for writing short dicts
        if extrasaction.lower() not in ("raise", "ignore"):
            raise ValueError, \
                  ("extrasaction (%s) must be 'raise' or 'ignore'" %
                   extrasaction)
        self.extrasaction = extrasaction
        self.queue = StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, *args, **kwds)
        self.stream = csvfile
        self.encoder = codecs.getincrementalencoder(encoding)()

    def _dict_to_list(self, rowdict):
        if self.extrasaction == "raise":
            wrong_fields = [k for k in rowdict if k not in self.fieldnames]
            if wrong_fields:
                raise ValueError("dict contains fields not in fieldnames: "
                                 + ", ".join([repr(x) for x in wrong_fields]))
        return [rowdict.get(key, self.restval) for key in self.fieldnames]

    def writeheader(self):
        header = dict(zip(self.fieldnames, self.fieldnames))
        self.writerow(header)

    def _encoder(self, data):
            if hasattr(data, 'encode'):
                return data.encode("utf-8")
            else:
                return data

    def writerow(self, rowdict):
        row = self._dict_to_list(rowdict)
        self.writer.writerow([self._encoder(s) for s in row])
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        data = self.encoder.encode(data)
        self.stream.write(data)
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

