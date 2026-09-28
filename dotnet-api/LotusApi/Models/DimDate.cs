using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class DimDate
{
    public long? DateId { get; set; }

    public string? FullDate { get; set; }

    public long? Day { get; set; }

    public long? Month { get; set; }

    public string? MonthName { get; set; }

    public long? Quarter { get; set; }

    public string? QuarterName { get; set; }

    public long? Year { get; set; }

    public long? DayOfWeek { get; set; }

    public string? DayName { get; set; }

    public long? IsWeekend { get; set; }

    public long? WeekOfYear { get; set; }

    public long? IsRamadan { get; set; }

    public string? BatchId { get; set; }
}
