n=3
a=[[1,3,7],[3,8],[6,12]]
within=2
b=[0,0,0] # 临时的结果
ans=[]

def dfs(k,a,b,n,ans,within):
    # global a,within,n,b,ans
    if(k==n):
        for i in range(n-1):
            if not (b[i+1]-b[i]>0 and b[i+1]-b[i]<=(within+1)):
                return
        ans.append(b[:])
    else:
        for i in a[k]:
            b[k]=i
            dfs(k+1,a,b,n,ans,within)

dfs(0,a,b,n,ans,within)
print(ans)
