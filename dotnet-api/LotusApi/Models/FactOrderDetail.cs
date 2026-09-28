using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class FactOrderDetail
{
    public string? DetailId { get; set; }

    public string? OrderId { get; set; }

    public string? ProductId { get; set; }

    public long? Quantity { get; set; }

    public long? UnitPrice { get; set; }

    public long? DiscountPct { get; set; }

    public double? SellingPrice { get; set; }

    public long? UnitCost { get; set; }

    public double? LineTotalRevenue { get; set; }

    public long? LineTotalCost { get; set; }

    public string? BatchId { get; set; }
}
