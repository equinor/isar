import inspect
import typing


class Utilities:
    @staticmethod
    def compare_tuples(response_tuple, expected_tuple) -> bool:
        """
        Checks if two tuples are equal. If an expected element is a class
        the function check that the corresponding response is of the same type
        """
        flag = True
        if expected_tuple is None and response_tuple is None:
            return flag
        for value, expected_value in zip(response_tuple, expected_tuple):
            if not Utilities.compare_two_arguments(value, expected_value):
                flag = False
        return flag

    @staticmethod
    def compare_two_arguments(response_argument, expected_argument):
        if inspect.isclass(expected_argument):
            if not isinstance(response_argument, expected_argument):
                return False
        elif hasattr(expected_argument, "__origin__"):
            expected_value_type = expected_argument.__origin__
            expected_value_class = typing.get_args(expected_argument)
            if expected_value_type == list:
                for items in response_argument:
                    if not isinstance(items, expected_value_class):
                        return False
        else:
            if not response_argument == expected_argument:
                return False
        return True
