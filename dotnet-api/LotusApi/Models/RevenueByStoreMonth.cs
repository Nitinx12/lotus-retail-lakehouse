using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class RevenueByStoreMonth
{
    public long? StoreId { get; set; }

    public string? Month { get; set; }

    public decimal? Revenue { get; set; }

    public decimal? Cost { get; set; }

    public long? Orders { get; set; }
}
