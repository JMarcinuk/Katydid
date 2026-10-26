class DuplicateContentError(ValueError):
    pass

class TagInUseError(ValueError):
    def __init__(self, blocking_entries):
        self.blocking_entries = blocking_entries
        super().__init__(f"This tag is the only tag on {len(self.blocking_entries)} entries")

class DefaultTagError(ValueError):
    pass

class EntryValidationError(ValueError):
    def __init__(self, problem_list):
        self.problem_list = problem_list
        super().__init__(f"Entry could not validate due to the following problems: {self.problem_list}")

class CharLimitConflictError(ValueError):
    def __init__(self, conflicting_entries):
        self.conflicting_entries = conflicting_entries
        super().__init__(f"{len(conflicting_entries)} entries exceed the requested limit")