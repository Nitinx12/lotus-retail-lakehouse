using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class RamadanSeasonality
{
    public string? Month { get; set; }

    public long? IsRamadan { get; set; }

    public decimal? Revenue { get; set; }

    public long? Orders { get; set; }
}
