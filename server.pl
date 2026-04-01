use IO::Socket::INET;

my $root = "/Users/noahwinter/Desktop/Projects/square_root_game";
my $port = 3000;

my %mime = (
    html => "text/html",
    css  => "text/css",
    js   => "application/javascript",
    png  => "image/png",
    jpg  => "image/jpeg",
    ico  => "image/x-icon",
);

my $server = IO::Socket::INET->new(
    LocalPort => $port,
    Type      => SOCK_STREAM,
    Reuse     => 1,
    Listen    => 10,
) or die "Cannot bind to port $port: $!";

while (my $client = $server->accept()) {
    my $request = "";
    while (my $line = <$client>) {
        $request .= $line;
        last if $line eq "\r\n";
    }

    my ($path) = $request =~ /^GET\s+(\S+)/;
    $path ||= "/";
    $path = "/index.html" if $path eq "/";
    $path =~ s/\?.*//;
    $path =~ s/\.\.//g;

    my $file = $root . $path;
    my ($ext) = $file =~ /\.(\w+)$/;
    my $type = $mime{lc($ext) // ""} // "text/plain";

    if (-f $file) {
        open(my $fh, "<", $file) or do {
            print $client "HTTP/1.1 403 Forbidden\r\n\r\n";
            close $client; next;
        };
        local $/;
        my $body = <$fh>;
        close $fh;
        print $client "HTTP/1.1 200 OK\r\nContent-Type: $type\r\nContent-Length: " . length($body) . "\r\nConnection: close\r\n\r\n$body";
    } else {
        print $client "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nNot found: $path";
    }

    close $client;
}
