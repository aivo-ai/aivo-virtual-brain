from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import os
from typing import Optional

class GradeCalculator:
    """Utility to calculate default grade based on date of birth with configurable cutoff."""

    def __init__(self, cutoff_month: int = 9, cutoff_day: int = 1):
        """
        Initialize grade calculator with configurable cutoff date.

        Args:
            cutoff_month: Month for grade cutoff (default: September = 9)
            cutoff_day: Day for grade cutoff (default: 1st)
        """
        self.cutoff_month = int(os.getenv("GRADE_CUTOFF_MONTH", cutoff_month))
        self.cutoff_day = int(os.getenv("GRADE_CUTOFF_DAY", cutoff_day))

    def calculate_grade_default(self, dob: date, reference_date: Optional[date] = None) -> str:
        """
        Calculate default grade based on date of birth.

        Args:
            dob: Date of birth
            reference_date: Reference date for calculation (defaults to today)

        Returns:
            Grade level as string (e.g., "K", "1", "2", ..., "12")
        """
        if reference_date is None:
            reference_date = date.today()

        # Calculate age in years
        age = relativedelta(reference_date, dob).years

        # Determine school year based on cutoff
        current_year = reference_date.year
        if reference_date.month < self.cutoff_month or \
           (reference_date.month == self.cutoff_month and reference_date.day < self.cutoff_day):
            school_year = current_year - 1
        else:
            school_year = current_year

        # Calculate when child should start kindergarten (age 5 by cutoff)
        kindergarten_year = dob.year + 5
        if dob.month > self.cutoff_month or \
           (dob.month == self.cutoff_month and dob.day >= self.cutoff_day):
            kindergarten_year += 1

        # Calculate grade level
        grade_level = school_year - kindergarten_year

        # Handle edge cases
        if grade_level < 0:
            return "PreK"
        elif grade_level == 0:
            return "K"
        elif grade_level <= 12:
            return str(grade_level)
        else:
            return "12+"  # Post-secondary

    def get_age_in_years(self, dob: date, reference_date: Optional[date] = None) -> int:
        """Get age in years for a given date of birth."""
        if reference_date is None:
            reference_date = date.today()
        return relativedelta(reference_date, dob).years

# Global instance with default configuration
grade_calculator = GradeCalculator()
