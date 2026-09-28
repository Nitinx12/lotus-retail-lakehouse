using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class ReturnRateByProduct
{
    public string? ProductId { get; set; }

    public long? TimesOrdered { get; set; }

    public long? TimesReturned { get; set; }

    public decimal? ReturnRate { get; set; }
}
