using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class DimProduct
{
    public string? ProductId { get; set; }

    public string? Category { get; set; }

    public string? Subcategory { get; set; }

    public string? Brand { get; set; }

    public long? UnitPrice { get; set; }

    public long? UnitCost { get; set; }

    public long? StockQty { get; set; }

    public long? IsActive { get; set; }

    public string? BatchId { get; set; }

    public string? ProductName { get; set; }

    public string? Color { get; set; }

    public string? Size { get; set; }
}
