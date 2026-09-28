using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class ExtractCheckpoint
{
    public string SourceCollection { get; set; } = null!;

    public string? LastObjectId { get; set; }

    public DateTime? LastLoadedAt { get; set; }

    public long RowsCopied { get; set; }

    public DateTime UpdatedAt { get; set; }
}
