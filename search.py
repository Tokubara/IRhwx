n=3
a=[[1,2],[3,4],[5,6]]
within=2
b=[0,0,0] # 临时的结果
ans=[]

def dfs(k,within,n,b,ans):
    global a
    if(k==n):
        print(b)
        if not (b[0]%2==0 and b[1]%2==1 and b[2]%2==0):
            return False
        return True
    else:
        for i in a[k]:
            b[k]=i
            if(dfs(k+1,within,n,b,ans)):
                return True

dfs(0,within,n,b,ans)
# print(ans)
