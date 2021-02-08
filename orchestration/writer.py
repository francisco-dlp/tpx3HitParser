import logging
import queue
import signal
from multiprocessing import Process
import lib


class Writer(Process):

    def __init__(self, settings, keep_processing, finalise_writing, oq, fq):
        Process.__init__(self)

        self.settings = settings
        self.output_queue = oq
        self.finished_queue = fq
        self.keep_processing = keep_processing
        self.finalise_writing = finalise_writing
        self.logger = logging.getLogger('root')
        self.io = lib.io()

    def run(self):
        # Ignore the interrupt signal. Let parent handle that.
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        # Open output file
        try:
            self.io.open_write(self.settings.output, self.settings.overwrite)
        except lib.IOException as e:
            self.logger.error(str(e))
            return 1

        while self.keep_processing.is_set():
            try:
                data = self.output_queue.get(timeout=1)
            except queue.Empty:
                if self.finalise_writing.is_set():
                    break
                else:
                    continue

            if self.settings.store_hits and 'hits' in data:
                self.write_hits(data['hits'])

            self.finished_queue.put(data['n_hits'])

            self.output_queue.task_done()

        # Finish writing, and close file
        self.finalise()

    def finalise(self):
        if self.settings.store_hits:
            self.io.store_hits(self.settings.raw)

        self.io.close_write()

    def write_hits(self, hits):
        self.io.write_hit_chunk(hits)
