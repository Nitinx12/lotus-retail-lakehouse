using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class DimStore
{
    public long? StoreId { get; set; }

    public string? StoreName { get; set; }

    public string? City { get; set; }

    public string? District { get; set; }

    public string? Region { get; set; }

    public long? OpeningYear { get; set; }

    public long? SizeSqm { get; set; }

    public string? StoreType { get; set; }

    public string? BatchId { get; set; }
}
